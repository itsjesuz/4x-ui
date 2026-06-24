import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Progress, Tag } from 'antd';
import { ClockCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';

import './SubUsageSummary.css';

interface SubUsageSummaryProps {
  usedByte: number;
  totalByte: number;
  usedLabel: string;
  totalLabel: string;
  remainedLabel: string;
  expireMs: number;
  isActive: boolean;
}

function pickStrokeColor(pct: number): Record<string, string> {
  if (pct >= 90) return { '0%': '#ff3b30', '100%': '#ff7b72' }; // iOS red to coral
  if (pct >= 75) return { '0%': '#ff9500', '100%': '#ffcc00' }; // iOS orange to yellow
  return { '0%': '#34c759', '100%': '#00d2ff' }; // iOS green to cyan-blue
}

function formatExpiryChip(expireMs: number): { label: string; color: string } | null {
  if (expireMs <= 0) return null;
  const diff = expireMs - Date.now();
  if (diff <= 0) return { label: 'Expired', color: 'red' };
  const days = Math.floor(diff / 86400000);
  if (days >= 1) return { label: `${days}d`, color: days <= 3 ? 'orange' : 'blue' };
  const hours = Math.max(1, Math.floor(diff / 3600000));
  return { label: `${hours}h`, color: 'orange' };
}

export default function SubUsageSummary({
  usedByte,
  totalByte,
  usedLabel,
  totalLabel,
  remainedLabel,
  expireMs,
  isActive,
}: SubUsageSummaryProps) {
  const { t } = useTranslation();
  const pct = useMemo(() => {
    if (totalByte <= 0) return 0;
    const v = (usedByte / totalByte) * 100;
    if (!Number.isFinite(v)) return 0;
    return Math.max(0, Math.min(100, v));
  }, [usedByte, totalByte]);

  const expiry = formatExpiryChip(expireMs);
  const isUnlimited = totalByte <= 0;
  const stroke = pickStrokeColor(pct);

  const pctClass = useMemo(() => {
    if (pct >= 90) return 'pct-red';
    if (pct >= 75) return 'pct-orange';
    return 'pct-green';
  }, [pct]);

  return (
    <div className={`usage-summary ${!isActive ? 'is-inactive' : ''}`}>
      <div className="usage-summary-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        
        {/* Left Side: Usage details & metadata */}
        <div className="usage-summary-details" style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1, minWidth: 0 }}>
          <div className="usage-summary-labels">
            <span className="usage-summary-used">{usedLabel}</span>
            <span className="usage-summary-sep">/</span>
            <span className="usage-summary-total">{isUnlimited ? '∞' : totalLabel}</span>
          </div>
          
          {!isUnlimited && (
            <div className="usage-summary-remained-text" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              {remainedLabel}
            </div>
          )}
          
          <div className="usage-summary-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '2px' }}>
            {isUnlimited && (
              <Tag color="purple" icon={<ThunderboltOutlined />}>
                {t('subscription.unlimited')}
              </Tag>
            )}
            {expiry && (
              <Tag color={expiry.color} icon={<ClockCircleOutlined />}>
                {expiry.label}
              </Tag>
            )}
          </div>
        </div>

        {/* Right Side: Circular progress indicator */}
        {!isUnlimited && (
          <div className={`usage-summary-circle ${pctClass}`} style={{ flexShrink: 0 }}>
            <Progress
              type="circle"
              percent={pct}
              showInfo={true}
              strokeColor={stroke}
              trailColor="var(--separator)"
              strokeWidth={7}
              strokeLinecap="round"
              width={112}
              format={(percent) => (
                <div className="usage-circle-inner">
                  <span className="usage-circle-percent">
                    {percent?.toFixed(0)}%
                  </span>
                  <span className="usage-circle-label">
                    {t('subscription.used') || 'Used'}
                  </span>
                </div>
              )}
            />
          </div>
        )}
      </div>
    </div>
  );
}
