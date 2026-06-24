import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Card,
  Col,
  ConfigProvider,
  Dropdown,
  Layout,
  Menu,
  message,
  Popover,
  QRCode,
  Row,
  Space,
  Tag,
} from 'antd';
import {
  AndroidOutlined,
  AppleOutlined,
  CopyOutlined,
  DownOutlined,
  MoonFilled,
  MoonOutlined,
  QrcodeOutlined,
  SunOutlined,
  TranslationOutlined,
  CheckCircleFilled,
  SendOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  ArrowDownOutlined,
  ArrowUpOutlined,
  SyncOutlined,
  SearchOutlined,
  FilterOutlined,
} from '@ant-design/icons';

import { ClipboardManager, IntlUtil, LanguageManager } from '@/utils';
import { isPostQuantumLink } from '@/lib/xray/inbound-link';
import { parseLinkParts } from '@/lib/xray/link-label';
import { setMessageInstance } from '@/utils/messageBus';
import { pauseAnimationsUntilLeave, useTheme } from '@/hooks/useTheme';
import SubUsageSummary from './SubUsageSummary';
import './SubPage.css';
import defaultLogoUrl from '@/assets/netfly-logo.png';

const QR_SIZE = 240;

function CountUpByte({ targetVal }: { targetVal: string | number }) {
  const [val, setVal] = useState(0);
  const numericTarget = typeof targetVal === 'string' ? parseFloat(targetVal.toString().replace(/,/g, '')) : targetVal;
  const suffix = typeof targetVal === 'string' ? targetVal.replace(/[0-9.,]/g, '').trim() : '';
  
  useEffect(() => {
    if (isNaN(numericTarget) || numericTarget === 0) {
      setVal(numericTarget);
      return;
    }
    const duration = 1500;
    const startT = performance.now();
    let frame: number;
    const tick = (t: number) => {
      const elapsed = t - startT;
      const progress = Math.min(elapsed / duration, 1);
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setVal(numericTarget * ease);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [numericTarget]);
  
  if (isNaN(numericTarget)) return <span>{targetVal}</span>;
  const displayVal = (numericTarget % 1 !== 0 || val % 1 !== 0) ? val.toFixed(2) : Math.round(val).toString();
  return <span>{displayVal} {suffix}</span>;
}

function CopyButton({ text, label, title }: { text: string, label?: string, title?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    if (!text) return;
    await ClipboardManager.copyText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <Button 
      size="small" 
      icon={copied ? <CheckCircleFilled /> : <CopyOutlined />} 
      onClick={handleCopy} 
      aria-label={label || 'Copy'} 
      title={title || 'Copy'} 
      className={`copy-btn ${copied ? 'copied-anim' : ''}`}
    />
  );
}

function AccordionItem({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="ios-accordion-item" style={{ borderBottom: '1px solid var(--separator)' }}>
      <div 
        className="ios-accordion-header" 
        onClick={() => setOpen(!open)}
        style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          padding: '14px 16px', 
          cursor: 'pointer',
          userSelect: 'none'
        }}
      >
        <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)', textAlign: 'left' }}>{title}</span>
        <span style={{ 
          fontSize: '10px', 
          color: 'var(--text-secondary)',
          transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
          transition: 'transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
          marginInlineStart: '8px'
        }}>
          ▶
        </span>
      </div>
      <div style={{
        maxHeight: open ? '800px' : '0',
        overflow: 'hidden',
        transition: 'max-height 0.3s cubic-bezier(0.16, 1, 0.3, 1), padding 0.3s ease',
        padding: open ? '0 16px 14px 16px' : '0 16px'
      }}>
        <div style={{ 
          fontSize: '13px', 
          color: 'var(--text-secondary)', 
          lineHeight: 1.6, 
          whiteSpace: 'pre-line',
          textAlign: 'justify'
        }}>
          {children}
        </div>
      </div>
    </div>
  );
}

function getProtocolBadgeClass(protocol: string) {
  const p = (protocol || '').toLowerCase();
  switch (p) {
    case 'vless': return 'sub-tag-vless';
    case 'vmess': return 'sub-tag-vmess';
    case 'trojan': return 'sub-tag-trojan';
    case 'shadowsocks': return 'sub-tag-shadowsocks';
    case 'hysteria2': case 'hysteria': return 'sub-tag-hysteria2';
    case 'tuic': return 'sub-tag-tuic';
    default: return 'sub-tag-link';
  }
}

const subData = window.__SUB_PAGE_DATA__ || {};

const subPageName = subData.subPageName || 'NetFly | نتفلای';
const subPageLogo = subData.subPageLogo || '';
const logoUrl = subPageLogo || defaultLogoUrl;
const subPageChannel = subData.subPageChannel || 'netflyco';
const subPageBot = subData.subPageBot || 'inetflybot';

const sId = subData.sId || '';
const enabled = !!subData.enabled;
const download = subData.download || '0';
const upload = subData.upload || '0';
const total = subData.total || '∞';
const used = subData.used || '0';
const remained = subData.remained || '';
const totalByte = Number(subData.totalByte || 0);
const expireMs = Number(subData.expire || 0) * 1000;
const lastOnlineMs = Number(subData.lastOnline || 0);
const subUrl = subData.subUrl || '';
const subJsonUrl = subData.subJsonUrl || '';
const subClashUrl = subData.subClashUrl || '';
const subTitle = subData.subTitle || '';
const links: string[] = Array.isArray(subData.links) ? subData.links : [];
const linkEmails: string[] = Array.isArray(subData.emails) ? subData.emails : [];
const datepicker = subData.datepicker || 'gregorian';
const telegramUsername = subData.telegramUsername || '';
const telegramFirstName = subData.telegramFirstName || '';
const telegramLastName = subData.telegramLastName || '';
const orderNumber = subData.orderNumber || '';

const isUnlimited = totalByte <= 0 && expireMs === 0;
const isActive = (() => {
  if (!enabled) return false;
  if (totalByte > 0) {
    const usedByteCalc = Number(subData.usedByte || 0)
      || (Number(subData.downloadByte || 0) + Number(subData.uploadByte || 0));
    if (usedByteCalc >= totalByte) return false;
  }
  if (expireMs > 0 && Date.now() >= expireMs) return false;
  return true;
})();

export default function SubPage() {
  const { t } = useTranslation();
  const { isDark, isUltra, antdThemeConfig } = useTheme();
  const [messageApi, messageContextHolder] = message.useMessage();
  useEffect(() => { setMessageInstance(messageApi); }, [messageApi]);

  const [lang, setLang] = useState<string>(() => LanguageManager.getLanguage());
  const [subTheme, setSubTheme] = useState<'light' | 'dark' | 'ultra' | 'grid-tech'>(() => {
    if (isUltra) return 'ultra';
    if (isDark) return 'dark';
    return 'light';
  });

  const onLangChange = useCallback((next: string) => {
    setLang(next);
    LanguageManager.setLanguage(next);
  }, []);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProtocol, setSelectedProtocol] = useState('all');

  const parsedNodes = useMemo(() => {
    return links.map((link, idx) => {
      const parts = parseLinkParts(link, linkEmails[idx] || '');
      const fallback = `Link ${idx + 1}`;
      const rowTitle = parts?.remark || fallback;
      const protocolName = (parts?.protocol || 'link').toLowerCase();
      const canQr = !isPostQuantumLink(link);
      const qrLabel = [parts?.remark, linkEmails[idx]].filter(Boolean).join('-') || rowTitle;
      return {
        link,
        idx,
        rowTitle,
        protocolName,
        canQr,
        qrLabel,
      };
    });
  }, []);

  const availableProtocols = useMemo(() => {
    const set = new Set<string>();
    parsedNodes.forEach((node) => {
      if (node.protocolName) {
        set.add(node.protocolName);
      }
    });
    return Array.from(set);
  }, [parsedNodes]);

  const filteredNodes = useMemo(() => {
    return parsedNodes.filter((node) => {
      const matchesSearch =
        node.rowTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.protocolName.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesProtocol = selectedProtocol === 'all' || node.protocolName === selectedProtocol;
      return matchesSearch && matchesProtocol;
    });
  }, [parsedNodes, searchQuery, selectedProtocol]);

  const filteredCopyText = useMemo(() => {
    return filteredNodes.map((n) => n.link).join('\n');
  }, [filteredNodes]);

  const cycleTheme = useCallback(() => {
    pauseAnimationsUntilLeave('sub-theme-cycle');
    setSubTheme((prev) => {
      if (prev === 'light') return 'dark';
      if (prev === 'dark') return 'ultra';
      if (prev === 'ultra') return 'grid-tech';
      return 'light';
    });
  }, []);

  const copy = useCallback(async (value: string) => {
    if (!value) return;
    const ok = await ClipboardManager.copyText(value);
    if (ok) messageApi.success(t('copied'));
  }, [t, messageApi]);


  const open = useCallback((url: string) => {
    if (!url) return;
    window.open(url, '_blank');
  }, []);

  const shadowrocketUrl = useMemo(() => {
    if (!subUrl) return '';
    const separator = subUrl.includes('?') ? '&' : '?';
    const rawUrl = subUrl + separator + 'flag=shadowrocket';
    const base64Url = btoa(rawUrl);
    const remark = encodeURIComponent(subTitle || sId || 'Subscription');
    return `shadowrocket://add/sub/${base64Url}?remark=${remark}`;
  }, []);

  const v2boxUrl = useMemo(
    () => `v2box://install-sub?url=${encodeURIComponent(subUrl)}&name=${encodeURIComponent(sId)}`,
    [],
  );
  const streisandUrl = useMemo(() => `streisand://import/${encodeURIComponent(subUrl)}`, []);
  const happUrl = useMemo(() => `happ://add/${subUrl}`, []);

  const pageClass = useMemo(() => {
    const classes = ['subscription-page'];
    classes.push(`theme-${subTheme}`);
    if (subTheme === 'dark' || subTheme === 'ultra' || subTheme === 'grid-tech') {
      classes.push('is-dark');
    }
    if (subTheme === 'ultra') {
      classes.push('is-ultra');
    }
    if (subTheme === 'grid-tech') {
      classes.push('is-grid-tech');
    }
    return classes.join(' ');
  }, [subTheme]);

  const androidMenuItems = useMemo(() => [
    {
      key: 'android-v2box',
      label: 'V2Box',
      onClick: () => open(`v2box://install-sub?url=${encodeURIComponent(subUrl)}&name=${encodeURIComponent(sId)}`),
    },
    {
      key: 'android-v2rayng',
      label: 'V2RayNG',
      onClick: () => open(`v2rayng://install-config?url=${encodeURIComponent(subUrl)}`),
    },
    { key: 'android-singbox', label: 'Sing-box', onClick: () => copy(subUrl) },
    { key: 'android-v2raytun', label: 'V2RayTun', onClick: () => copy(subUrl) },
    { key: 'android-npvtunnel', label: 'NPV Tunnel', onClick: () => copy(subUrl) },
    { key: 'android-happ', label: 'Happ', onClick: () => open(`happ://add/${subUrl}`) },
  ], [copy, open]);

  const iosMenuItems = useMemo(() => [
    { key: 'ios-shadowrocket', label: 'Shadowrocket', onClick: () => open(shadowrocketUrl) },
    { key: 'ios-v2box', label: 'V2Box', onClick: () => open(v2boxUrl) },
    { key: 'ios-streisand', label: 'Streisand', onClick: () => open(streisandUrl) },
    { key: 'ios-v2raytun', label: 'V2RayTun', onClick: () => copy(subUrl) },
    { key: 'ios-npvtunnel', label: 'NPV Tunnel', onClick: () => copy(subUrl) },
    { key: 'ios-happ', label: 'Happ', onClick: () => open(happUrl) },
  ], [copy, open, shadowrocketUrl, v2boxUrl, streisandUrl, happUrl]);

  const langMenuItems = useMemo(
    () => (LanguageManager.supportedLanguages as { value: string; name: string; icon: string }[]).map((l) => ({
      key: l.value,
      label: (
        <Space size={8}>
          <span aria-hidden="true">{l.icon}</span>
          <span>{l.name}</span>
        </Space>
      ),
    })),
    [],
  );

  const themeIcon = useMemo(() => {
    if (subTheme === 'light') return <SunOutlined />;
    if (subTheme === 'dark') return <MoonOutlined />;
    if (subTheme === 'ultra') return <MoonFilled />;
    return <ThunderboltOutlined style={{ color: '#00ff66' }} />;
  }, [subTheme]);

  const activeThemeConfig = useMemo(() => {
    const base = antdThemeConfig;
    if (subTheme === 'grid-tech') {
      return {
        ...base,
        token: {
          ...base.token,
          colorPrimary: '#00ff66', // Tech Green
          colorLink: '#00f2fe',    // Tech Cyan
        },
      };
    }
    if (subTheme === 'light') {
      return {
        ...base,
        token: {
          ...base.token,
          colorPrimary: '#007aff', // Classic iOS Blue
        },
      };
    }
    return base;
  }, [antdThemeConfig, subTheme]);

  const cardTitle = (
    <Space>
      <span>{t('subscription.title')}</span>
      <Tag>{orderNumber || sId}</Tag>
    </Space>
  );

  const cardExtra = (
    <Space size={8} align="center">
      <Button
        shape="circle"
        size="large"
        className="toolbar-btn"
        aria-label={t('menu.theme')}
        title={t('menu.theme')}
        icon={themeIcon}
        onClick={cycleTheme}
      />
      <Popover
        rootClassName={`glass-menu-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
        overlayClassName={`glass-menu-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
        placement="bottomRight"
        trigger="click"
        styles={{ content: { padding: 4 } }}
        content={
          <Menu
            mode="vertical"
            selectable
            selectedKeys={[lang]}
            items={langMenuItems}
            onClick={({ key }) => onLangChange(key)}
            style={{ border: 'none', minWidth: 160 }}
          />
        }
      >
        <Button
          shape="circle"
          size="large"
          className="toolbar-btn"
          aria-label={t('pages.settings.language')}
          icon={<TranslationOutlined />}
        />
      </Popover>
    </Space>
  );

  return (
    <ConfigProvider theme={activeThemeConfig}>
      {messageContextHolder}
      <Layout className={pageClass}>
        <div className="subscription-page-bg-orb-3" />
        <Layout.Content className="content">
          <Row justify="center">
            <Col xs={24} sm={22} md={18} lg={14} xl={12}>
              <Card bordered={false} className="subscription-card" title={cardTitle} extra={cardExtra}>
                
                <div className="company-header">
                  <div className="header-waves">
                    <svg className="waves-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 24 150 28" preserveAspectRatio="none" shapeRendering="auto">
                      <defs>
                        <path id="gentle-wave" d="M-160 44c30 0 58-18 88-18s58 18 88 18 58-18 88-18 58 18 88 18v44h-352z" />
                      </defs>
                      <g className="parallax">
                        <use href="#gentle-wave" x="48" y="0" />
                        <use href="#gentle-wave" x="48" y="3" />
                        <use href="#gentle-wave" x="48" y="5" />
                        <use href="#gentle-wave" x="48" y="7" />
                      </g>
                    </svg>
                  </div>
                  <img src={logoUrl} alt={subPageName} className="company-logo" />
                  <h1 className="company-title">{subPageName}</h1>
                  
                  {/* Telegram Bot User Profile Card */}
                  {(telegramFirstName || telegramUsername) && (
                    <div className="ios-profile-card">
                      <div className="ios-profile-avatar-container">
                        <div className="ios-profile-avatar">
                          {telegramFirstName ? telegramFirstName.charAt(0).toUpperCase() : '?'}
                        </div>
                        {enabled && isActive && (
                          <span className="ios-profile-status-badge" />
                        )}
                      </div>
                      <div className="ios-profile-info">
                        <div className="ios-profile-name-row">
                          <span className="ios-profile-name">
                            {[telegramFirstName, telegramLastName].filter(Boolean).join(' ')}
                          </span>
                          {orderNumber && (
                            <span className="ios-order-badge">{orderNumber}</span>
                          )}
                        </div>
                        {telegramUsername && (
                          <span className="ios-profile-username">
                            <SendOutlined className="telegram-inline-icon" />
                            @{telegramUsername}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="company-socials">
                    {subPageBot && (
                      <a href={`https://t.me/${subPageBot}`} target="_blank" rel="noopener noreferrer">
                        <Button size="small" className="social-btn" icon={<SendOutlined />}>@{subPageBot}</Button>
                      </a>
                    )}
                    {subPageChannel && (
                      <a href={`https://t.me/${subPageChannel}`} target="_blank" rel="noopener noreferrer">
                        <Button size="small" className="social-btn" icon={<SendOutlined />}>@{subPageChannel}</Button>
                      </a>
                    )}
                  </div>
                </div>

                {/* iOS Info Cards Grid */}
                <div className="ios-metrics-grid">
                  <div className="ios-metric-box">
                    <div className="ios-metric-header">
                      <span className="ios-metric-label">{t('subscription.status')}</span>
                      <div className={`ios-metric-icon ${!enabled ? 'status-inactive' : isUnlimited ? 'status-unlimited' : isActive ? 'status-active' : 'status-inactive'}`}>
                        <ThunderboltOutlined />
                      </div>
                    </div>
                    <span className="ios-metric-value">
                      {!enabled ? (
                        <>
                          <span className="status-dot inactive" />
                          <span style={{ color: '#ff3b30' }}>{t('subscription.inactive')}</span>
                        </>
                      ) : isUnlimited ? (
                        <>
                          <span className="status-dot unlimited" />
                          <span style={{ color: '#af52de' }}>{t('subscription.unlimited')}</span>
                        </>
                      ) : (
                        <>
                          <span className={`status-dot ${isActive ? 'active' : 'inactive'}`} />
                          <span style={{ color: isActive ? '#34c759' : '#ff3b30' }}>
                            {isActive ? t('subscription.active') : t('subscription.inactive')}
                          </span>
                        </>
                      )}
                    </span>
                  </div>
                  <div className="ios-metric-box">
                    <div className="ios-metric-header">
                      <span className="ios-metric-label">{t('subscription.expiry')}</span>
                      <div className="ios-metric-icon expiry">
                        <ClockCircleOutlined />
                      </div>
                    </div>
                    <span className="ios-metric-value" style={{ fontSize: '13px' }}>
                      {expireMs === 0 ? t('subscription.noExpiry') : IntlUtil.formatDate(expireMs, datepicker)}
                    </span>
                  </div>
                  <div className="ios-metric-box">
                    <div className="ios-metric-header">
                      <span className="ios-metric-label">{t('subscription.downloaded')}</span>
                      <div className="ios-metric-icon download">
                        <ArrowDownOutlined />
                      </div>
                    </div>
                    <span className="ios-metric-value"><CountUpByte targetVal={download} /></span>
                  </div>
                  <div className="ios-metric-box">
                    <div className="ios-metric-header">
                      <span className="ios-metric-label">{t('subscription.uploaded')}</span>
                      <div className="ios-metric-icon upload">
                        <ArrowUpOutlined />
                      </div>
                    </div>
                    <span className="ios-metric-value"><CountUpByte targetVal={upload} /></span>
                  </div>
                  
                  {/* Last Online Metric Box */}
                  <div className="ios-metric-box ios-metric-full">
                    <div className="ios-metric-header">
                      <span className="ios-metric-label">{t('lastOnline')}</span>
                      <div className="ios-metric-icon online">
                        <SyncOutlined />
                      </div>
                    </div>
                    <span className="ios-metric-value">
                      {lastOnlineMs > 0 ? IntlUtil.formatDate(lastOnlineMs, datepicker) : '-'}
                    </span>
                  </div>
                </div>

                <SubUsageSummary
                  usedByte={Number(subData.usedByte || 0)
                    || (Number(subData.downloadByte || 0) + Number(subData.uploadByte || 0))}
                  totalByte={totalByte}
                  usedLabel={used}
                  totalLabel={total}
                  remainedLabel={remained}
                  expireMs={expireMs}
                  isActive={isActive}
                />

                {/* Profiles Section */}
                {(subUrl || subJsonUrl || subClashUrl) && (
                  <>
                    <h2 className="ios-list-header">{t('subscription.title')}</h2>
                    <div className="ios-list-group">
                      {subUrl && (
                        <div className="ios-list-row">
                          <div className="ios-row-left">
                            <div className="ios-icon-wrapper sub-tag-sub">SUB</div>
                            <span className="ios-row-title" title={subUrl}>{sId || 'Subscription Link'}</span>
                          </div>
                          <div className="ios-row-right">
                            <CopyButton text={subUrl} label={t('copy')} title={t('copy')} />
                            <Popover
                              trigger="click"
                              placement="left"
                              destroyOnHidden
                              rootClassName={`glass-qr-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
                              overlayClassName={`glass-qr-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
                              content={
                                <div className="sub-link-qr-popover">
                                  <Tag color="green" className="qr-tag">{t('pages.settings.subSettings')}</Tag>
                                  <QRCode value={subUrl} size={QR_SIZE} type="svg" bordered={false} color={subTheme === 'grid-tech' ? "#00ff66" : (subTheme !== 'light' ? "#60a5fa" : "#007aff")} bgColor="transparent" icon={logoUrl} iconSize={40} />
                                </div>
                              }
                            >
                              <Button size="small" className="qr-btn" icon={<QrcodeOutlined />} aria-label="QR" title="QR" />
                            </Popover>
                          </div>
                        </div>
                      )}
                      {subJsonUrl && (
                        <div className="ios-list-row">
                          <div className="ios-row-left">
                            <div className="ios-icon-wrapper sub-tag-json">JSON</div>
                            <span className="ios-row-title" title={subJsonUrl}>JSON Link</span>
                          </div>
                          <div className="ios-row-right">
                            <CopyButton text={subJsonUrl} label={t('copy')} title={t('copy')} />
                            <Popover
                              trigger="click"
                              placement="left"
                              destroyOnHidden
                              rootClassName={`glass-qr-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
                              overlayClassName={`glass-qr-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
                              content={
                                <div className="sub-link-qr-popover">
                                  <Tag color="purple" className="qr-tag">{t('pages.settings.subSettings')} JSON</Tag>
                                  <QRCode value={subJsonUrl} size={QR_SIZE} type="svg" bordered={false} color={subTheme === 'grid-tech' ? "#00ff66" : (subTheme !== 'light' ? "#c084fc" : "#af52de")} bgColor="transparent" icon={logoUrl} iconSize={40} />
                                </div>
                              }
                            >
                              <Button size="small" className="qr-btn" icon={<QrcodeOutlined />} aria-label="QR" title="QR" />
                            </Popover>
                          </div>
                        </div>
                      )}
                      {subClashUrl && (
                        <div className="ios-list-row">
                          <div className="ios-row-left">
                            <div className="ios-icon-wrapper sub-tag-clash">CLSH</div>
                            <span className="ios-row-title" title={subClashUrl}>Clash / Mihomo Link</span>
                          </div>
                          <div className="ios-row-right">
                            <CopyButton text={subClashUrl} label={t('copy')} title={t('copy')} />
                            <Popover
                              trigger="click"
                              placement="left"
                              destroyOnHidden
                              rootClassName={`glass-qr-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
                              overlayClassName={`glass-qr-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
                              content={
                                <div className="sub-link-qr-popover">
                                  <Tag color="gold" className="qr-tag">Clash / Mihomo</Tag>
                                  <QRCode value={subClashUrl} size={QR_SIZE} type="svg" bordered={false} color={subTheme === 'grid-tech' ? "#00ff66" : (subTheme !== 'light' ? "#fbbf24" : "#ff9500")} bgColor="transparent" icon={logoUrl} iconSize={40} />
                                </div>
                              }
                            >
                              <Button size="small" className="qr-btn" icon={<QrcodeOutlined />} aria-label="QR" title="QR" />
                            </Popover>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* Nodes Section */}
                {links.length > 0 && (
                  <>
                    <h2 className="ios-list-header">{t('pages.inbounds.copyLink')}</h2>
                    
                    {/* iOS Search & Filter Controls */}
                    <div className="ios-search-filter-container">
                      <div className="ios-search-wrapper">
                        <SearchOutlined className="ios-search-icon" />
                        <input
                          type="text"
                          className="ios-search-input"
                          placeholder={t('subscription.searchPlaceholder')}
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        {searchQuery && (
                          <button className="ios-search-clear" onClick={() => setSearchQuery('')}>
                            ✕
                          </button>
                        )}
                      </div>
                      
                      {availableProtocols.length > 0 && (
                        <div className="ios-filter-pills">
                          <button
                            type="button"
                            className={`ios-filter-pill ${selectedProtocol === 'all' ? 'active' : ''}`}
                            onClick={() => setSelectedProtocol('all')}
                          >
                            {t('all')}
                          </button>
                          {availableProtocols.map((proto) => (
                            <button
                              type="button"
                              key={proto}
                              className={`ios-filter-pill ${selectedProtocol === proto ? 'active' : ''}`}
                              onClick={() => setSelectedProtocol(proto)}
                            >
                              {proto.toUpperCase()}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>

                    {filteredNodes.length === 0 ? (
                      <div className="ios-empty-filter">
                        <FilterOutlined style={{ fontSize: '24px', marginBottom: '8px', color: 'var(--text-tertiary)' }} />
                        <div>{t('subscription.noConfigsFound')}</div>
                      </div>
                    ) : (
                      <div className="ios-list-group">
                        <div className="ios-list-row copy-all-row">
                          <div className="ios-row-left">
                            <div className="ios-icon-wrapper sub-tag-all">ALL</div>
                            <span className="ios-row-title" style={{ fontWeight: 'bold' }}>{t('subscription.copyAll')}</span>
                          </div>
                          <div className="ios-row-right">
                            <CopyButton text={filteredCopyText} label={t('subscription.copyAll')} title={t('subscription.copyAll')} />
                          </div>
                        </div>
                        {filteredNodes.map((node) => {
                          return (
                            <div key={node.link} className="ios-list-row">
                              <div className="ios-row-left">
                                <div className={`ios-icon-wrapper ${getProtocolBadgeClass(node.protocolName)}`}>
                                  {node.protocolName.substring(0, 3).toUpperCase()}
                                </div>
                                <span className="ios-row-title" title={node.rowTitle}>{node.rowTitle}</span>
                              </div>
                              <div className="ios-row-right">
                                <CopyButton text={node.link} label={t('copy')} title={t('copy')} />
                                {node.canQr && (
                                  <Popover
                                    trigger="click"
                                    placement="left"
                                    destroyOnHidden
                                    rootClassName={`glass-qr-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
                                    overlayClassName={`glass-qr-popover sub-theme-${subTheme} ${subTheme === 'light' ? 'light' : 'dark'} ${subTheme === 'grid-tech' ? 'is-grid-tech' : ''} ${subTheme === 'ultra' ? 'is-ultra' : ''}`}
                                    content={
                                      <div className="sub-link-qr-popover">
                                        <Tag className="qr-tag">{node.qrLabel}</Tag>
                                        <QRCode
                                          value={node.link}
                                          size={220}
                                          type="svg"
                                          bordered={false}
                                          color={subTheme === 'grid-tech' ? "#00ff66" : (subTheme !== 'light' ? "#60a5fa" : "#007aff")}
                                          bgColor="transparent"
                                          icon={logoUrl}
                                          iconSize={40}
                                        />
                                      </div>
                                    }
                                  >
                                    <Button size="small" className="qr-btn" icon={<QrcodeOutlined />} aria-label="QR" title="QR" />
                                  </Popover>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}

                {/* Action Buttons */}
                <Row gutter={[8, 8]} justify="center" className="apps-row">
                  <Col xs={24} sm={12} className="app-col">
                    <Dropdown trigger={['click']} menu={{ items: androidMenuItems }}>
                      <Button className="ios-action-pill" size="large">
                        <AndroidOutlined /> Android <DownOutlined />
                      </Button>
                    </Dropdown>
                  </Col>
                  <Col xs={24} sm={12} className="app-col">
                    <Dropdown trigger={['click']} menu={{ items: iosMenuItems }}>
                      <Button className="ios-action-pill" size="large">
                        <AppleOutlined /> iOS <DownOutlined />
                      </Button>
                    </Dropdown>
                  </Col>
                </Row>

                {/* FAQ / Setup Section */}
                <h2 className="ios-list-header" style={{ marginTop: '24px' }}>
                  {t('subscription.faq.title')}
                </h2>
                <div className="ios-list-group" style={{ marginBottom: 0 }}>
                  <AccordionItem title={t('subscription.faq.iosTitle')}>
                    {t('subscription.faq.iosContent')}
                  </AccordionItem>
                  <AccordionItem title={t('subscription.faq.androidTitle')}>
                    {t('subscription.faq.androidContent')}
                  </AccordionItem>
                  <AccordionItem title={t('subscription.faq.desktopTitle')}>
                    {t('subscription.faq.desktopContent')}
                  </AccordionItem>
                  <AccordionItem title={t('subscription.faq.troubleTitle')}>
                    {t('subscription.faq.troubleContent')}
                  </AccordionItem>
                </div>
              </Card>
            </Col>
          </Row>
        </Layout.Content>

        {/* Floating Support Button */}
        <a 
          href="https://t.me/inetflybot"
          target="_blank" 
          rel="noopener noreferrer"
          className="ios-floating-support"
          title="Support"
        >
          <SendOutlined className="support-icon" />
        </a>
      </Layout>
    </ConfigProvider>
  );
}
