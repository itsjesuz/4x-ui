package controller

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"slices"
	"strconv"
	"strings"
	"time"

	"github.com/itsjesuz/4x-ui/internal/database"
	"github.com/itsjesuz/4x-ui/internal/database/model"
	"github.com/itsjesuz/4x-ui/internal/logger"
	"github.com/itsjesuz/4x-ui/internal/web/middleware"
	"github.com/itsjesuz/4x-ui/internal/web/runtime"
	"github.com/itsjesuz/4x-ui/internal/web/service"

	"github.com/gin-gonic/gin"
)

type NodeController struct {
	nodeService    service.NodeService
	inboundService service.InboundService
}

func NewNodeController(g *gin.RouterGroup) *NodeController {
	a := &NodeController{}
	a.initRouter(g)
	return a
}

func (a *NodeController) initRouter(g *gin.RouterGroup) {
	g.GET("/list", a.list)
	g.GET("/get/:id", a.get)
	g.GET("/webCert/:id", a.webCert)

	g.POST("/add", a.add)
	g.POST("/update/:id", a.update)
	g.POST("/del/:id", a.del)
	g.POST("/setEnable/:id", a.setEnable)

	g.POST("/test", a.test)
	g.POST("/certFingerprint", a.certFingerprint)
	g.POST("/inbounds", a.inbounds)
	g.POST("/probe/:id", a.probe)
	g.GET("/unsynced/:id", a.unsynced)
	g.POST("/sync/:id", a.sync)
	g.POST("/syncAll", a.syncAll)
	g.POST("/updatePanel", a.updatePanel)
	g.GET("/history/:id/:metric/:bucket", a.history)
}

func (a *NodeController) list(c *gin.Context) {
	nodes, err := a.nodeService.GetNodeTree()
	if err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.list"), err)
		return
	}
	jsonObj(c, nodes, nil)
}

func (a *NodeController) get(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	n, err := a.nodeService.GetById(id)
	if err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.obtain"), err)
		return
	}
	jsonObj(c, n, nil)
}

// webCert returns the node's own web TLS certificate/key file paths so the
// inbound form's "Set Cert from Panel" can fill paths that exist on the node.
func (a *NodeController) webCert(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	files, err := a.nodeService.GetWebCertFiles(id)
	if err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.obtain"), err)
		return
	}
	jsonObj(c, files, nil)
}

func (a *NodeController) ensureReachable(c *gin.Context, n *model.Node) error {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 6*time.Second)
	defer cancel()
	if _, err := a.nodeService.Probe(ctx, n); err != nil {
		return errors.New(service.FriendlyProbeError(err.Error()))
	}
	return nil
}

func (a *NodeController) add(c *gin.Context) {
	n, ok := middleware.BindAndValidate[model.Node](c)
	if !ok {
		return
	}
	if err := a.ensureReachable(c, n); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.add"), err)
		return
	}
	if err := a.nodeService.Create(n); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.add"), err)
		return
	}
	jsonMsgObj(c, I18nWeb(c, "pages.nodes.toasts.add"), n, nil)
}

func (a *NodeController) update(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	n, ok := middleware.BindAndValidate[model.Node](c)
	if !ok {
		return
	}
	if err := a.ensureReachable(c, n); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.update"), err)
		return
	}
	if err := a.nodeService.Update(id, n); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.update"), err)
		return
	}
	jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.update"), nil)
}

func (a *NodeController) del(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	if err := a.nodeService.Delete(id); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.delete"), err)
		return
	}
	jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.delete"), nil)
}

func (a *NodeController) setEnable(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	body := struct {
		Enable bool `json:"enable" form:"enable"`
	}{}
	if err := c.ShouldBind(&body); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.update"), err)
		return
	}
	if err := a.nodeService.SetEnable(id, body.Enable); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.update"), err)
		return
	}
	jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.update"), nil)
}

func (a *NodeController) inbounds(c *gin.Context) {
	n := &model.Node{}
	if err := c.ShouldBind(n); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.obtain"), err)
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()
	options, err := a.nodeService.GetRemoteInboundOptions(ctx, n)
	jsonObj(c, options, err)
}

func (a *NodeController) test(c *gin.Context) {
	n := &model.Node{}
	if err := c.ShouldBind(n); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.test"), err)
		return
	}
	if n.Scheme == "" {
		n.Scheme = "https"
	}
	if n.BasePath == "" {
		n.BasePath = "/"
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 6*time.Second)
	defer cancel()
	patch, err := a.nodeService.Probe(ctx, n)
	jsonObj(c, patch.ToUI(err == nil), nil)
}

func (a *NodeController) certFingerprint(c *gin.Context) {
	n := &model.Node{}
	if err := c.ShouldBind(n); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.test"), err)
		return
	}
	if n.Scheme == "" {
		n.Scheme = "https"
	}
	if n.BasePath == "" {
		n.BasePath = "/"
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), 6*time.Second)
	defer cancel()
	fp, err := a.nodeService.FetchCertFingerprint(ctx, n)
	if err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.test"), err)
		return
	}
	jsonObj(c, fp, nil)
}

func (a *NodeController) probe(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	n, err := a.nodeService.GetById(id)
	if err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.obtain"), err)
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 6*time.Second)
	defer cancel()
	patch, probeErr := a.nodeService.Probe(ctx, n)
	if probeErr != nil {
		patch.Status = "offline"
	} else {
		patch.Status = "online"
	}
	_ = a.nodeService.UpdateHeartbeat(id, patch)
	jsonObj(c, patch.ToUI(probeErr == nil), nil)
}

func (a *NodeController) updatePanel(c *gin.Context) {
	var req struct {
		Ids []int `json:"ids"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		jsonMsg(c, I18nWeb(c, "somethingWentWrong"), err)
		return
	}
	if len(req.Ids) == 0 {
		jsonMsg(c, I18nWeb(c, "somethingWentWrong"), fmt.Errorf("no nodes selected"))
		return
	}
	results, err := a.nodeService.UpdatePanels(req.Ids)
	jsonMsgObj(c, I18nWeb(c, "pages.nodes.toasts.updateStarted"), results, err)
}

func (a *NodeController) history(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	metric := c.Param("metric")
	if !slices.Contains(service.NodeMetricKeys, metric) {
		jsonMsg(c, "invalid metric", fmt.Errorf("unknown metric"))
		return
	}
	bucket, err := strconv.Atoi(c.Param("bucket"))
	if err != nil || bucket <= 0 || !service.IsAllowedHistoryBucket(bucket) {
		jsonMsg(c, "invalid bucket", fmt.Errorf("unsupported bucket"))
		return
	}
	jsonObj(c, a.nodeService.AggregateNodeMetric(id, metric, bucket, 60), nil)
}

func (a *NodeController) getUnsyncedClients(ctx context.Context, n *model.Node) (toAdd []string, toDelete []string, err error) {
	db := database.GetDB()
	var localInbounds []*model.Inbound
	if err := db.Model(model.Inbound{}).Where("node_id = ?", n.Id).Find(&localInbounds).Error; err != nil {
		return nil, nil, err
	}

	localEmails := make(map[string]struct{})
	for _, ib := range localInbounds {
		var settings map[string]any
		if err := json.Unmarshal([]byte(ib.Settings), &settings); err == nil && settings != nil {
			if clients, ok := settings["clients"].([]any); ok {
				for _, c := range clients {
					if cm, ok := c.(map[string]any); ok {
						if email, _ := cm["email"].(string); email != "" {
							localEmails[strings.ToLower(email)] = struct{}{}
						}
					}
				}
			}
		}
	}

	mgr := runtime.GetManager()
	if mgr == nil {
		return nil, nil, fmt.Errorf("runtime manager not initialized")
	}
	rt, err := mgr.RemoteFor(n)
	if err != nil {
		return nil, nil, err
	}

	snap, err := rt.FetchTrafficSnapshot(ctx)
	if err != nil {
		return nil, nil, err
	}

	remoteEmails := make(map[string]struct{})
	if snap != nil {
		for _, ib := range snap.Inbounds {
			var settings map[string]any
			if err := json.Unmarshal([]byte(ib.Settings), &settings); err == nil && settings != nil {
				if clients, ok := settings["clients"].([]any); ok {
					for _, c := range clients {
						if cm, ok := c.(map[string]any); ok {
							if email, _ := cm["email"].(string); email != "" {
								remoteEmails[strings.ToLower(email)] = struct{}{}
							}
						}
					}
				}
			}
		}
	}

	toAdd = make([]string, 0)
	toDelete = make([]string, 0)

	for email := range remoteEmails {
		if _, ok := localEmails[email]; !ok {
			toDelete = append(toDelete, email)
		}
	}

	for email := range localEmails {
		if _, ok := remoteEmails[email]; !ok {
			toAdd = append(toAdd, email)
		}
	}

	return toAdd, toDelete, nil
}

func (a *NodeController) unsynced(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	n, err := a.nodeService.GetById(id)
	if err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.obtain"), err)
		return
	}
	if !n.Enable {
		jsonMsg(c, "Node is disabled", fmt.Errorf("node is disabled"))
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 20*time.Second)
	defer cancel()

	toAdd, toDelete, err := a.getUnsyncedClients(ctx, n)
	if err != nil {
		jsonMsg(c, "Failed to get unsynced clients", err)
		return
	}

	jsonObj(c, gin.H{
		"toAdd":    toAdd,
		"toDelete": toDelete,
		"dirty":    n.ConfigDirty,
	}, nil)
}

func (a *NodeController) sync(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		jsonMsg(c, I18nWeb(c, "get"), err)
		return
	}
	n, err := a.nodeService.GetById(id)
	if err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.obtain"), err)
		return
	}
	if !n.Enable {
		jsonMsg(c, "Node is disabled", fmt.Errorf("node is disabled"))
		return
	}
	mgr := runtime.GetManager()
	if mgr == nil {
		jsonMsg(c, "Runtime manager not initialized", fmt.Errorf("no manager"))
		return
	}
	rt, err := mgr.RemoteFor(n)
	if err != nil {
		jsonMsg(c, "Could not resolve remote runtime for node", err)
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()

	_, toDelete, _ := a.getUnsyncedClients(ctx, n)

	if err := a.inboundService.ReconcileNode(ctx, rt, n); err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.syncFailed")+" ("+err.Error()+")", err)
		return
	}

	for _, email := range toDelete {
		_ = rt.DeleteClient(ctx, email)
	}

	// Clear node dirty flag on success
	if err := a.nodeService.ClearNodeDirty(n.Id, n.ConfigDirtyAt); err != nil {
		logger.Warning("sync: clear dirty for", n.Name, "failed:", err)
	}

	jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.syncSuccess"), nil)
}

func (a *NodeController) syncAll(c *gin.Context) {
	nodes, err := a.nodeService.GetAll()
	if err != nil {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.list"), err)
		return
	}
	mgr := runtime.GetManager()
	if mgr == nil {
		jsonMsg(c, "Runtime manager not initialized", fmt.Errorf("no manager"))
		return
	}

	var syncErrors []string
	for _, n := range nodes {
		if !n.Enable || n.Status != "online" {
			continue
		}
		rt, err := mgr.RemoteFor(n)
		if err != nil {
			syncErrors = append(syncErrors, fmt.Sprintf("%s: %s", n.Name, err))
			continue
		}
		ctx, cancel := context.WithTimeout(c.Request.Context(), 25*time.Second)
		_, toDelete, _ := a.getUnsyncedClients(ctx, n)
		if err := a.inboundService.ReconcileNode(ctx, rt, n); err != nil {
			syncErrors = append(syncErrors, fmt.Sprintf("%s: %s", n.Name, err))
		} else {
			for _, email := range toDelete {
				_ = rt.DeleteClient(ctx, email)
			}
			if err := a.nodeService.ClearNodeDirty(n.Id, n.ConfigDirtyAt); err != nil {
				logger.Warning("syncAll: clear dirty for", n.Name, "failed:", err)
			}
		}
		cancel()
	}

	if len(syncErrors) > 0 {
		jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.syncFailed")+" ("+strings.Join(syncErrors, "; ")+")", fmt.Errorf("partial success"))
		return
	}

	jsonMsg(c, I18nWeb(c, "pages.nodes.toasts.syncSuccess"), nil)
}
