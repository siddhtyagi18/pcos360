import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Brain,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  Droplet,
  FileText,
  HelpCircle,
  Info,
  LineChart as LineChartIcon,
  Moon,
  RefreshCw,
  Sparkles,
  Stethoscope,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  AreaChart,
  Area,
} from 'recharts';
import { useHealth } from '../context/HealthContext';
import { apiClient } from '../services/api';
import { Badge } from '../components/common/Badge';
import EthicalDisclaimer from '../components/common/EthicalDisclaimer';

export default function PcoscopePage() {
  const { authState, setIsLogModalOpen, setIsLabUploadModalOpen } = useHealth();
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'trends' | 'correlations' | 'biomarkers' | 'care-gaps'
  const [windowDays, setWindowDays] = useState(30);
  const [selectedMetric, setSelectedMetric] = useState('all');

  // Live Analysis & Insights State
  const [analysis, setAnalysis] = useState(null);
  const [insights, setInsights] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  const fetchPcoscopeData = useCallback(async (days = windowDays, isBackground = false) => {
    if (!isBackground) setIsLoading(true);
    else setIsRefreshing(true);
    setFetchError(null);

    try {
      const [analysisRes, insightsRes] = await Promise.all([
        apiClient.getPcoscopeAnalysis(days),
        apiClient.getPcoscopeInsights(days).catch((err) => {
          console.warn('AI Insights retrieval non-fatal:', err);
          return null;
        }),
      ]);

      setAnalysis(analysisRes);
      setInsights(insightsRes);
    } catch (err) {
      console.error('Failed to load PCOSCOPE data:', err);
      setFetchError(err.message || 'Could not load pattern discovery data.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [windowDays]);

  useEffect(() => {
    fetchPcoscopeData(windowDays);
  }, [fetchPcoscopeData, windowDays]);

  const handleWindowChange = (days) => {
    setWindowDays(days);
    fetchPcoscopeData(days);
  };

  // Helper for trend badge color
  const getTrendBadge = (trend) => {
    switch (trend) {
      case 'Improving':
        return <Badge variant="green" size="xs">Improving</Badge>;
      case 'Worsening':
        return <Badge variant="pink" size="xs">Worsening</Badge>;
      case 'Stable':
        return <Badge variant="purple" size="xs">Stable</Badge>;
      case 'Increasing':
        return <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md"><ArrowUp className="w-3 h-3" /> Increasing</span>;
      case 'Decreasing':
        return <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md"><ArrowDown className="w-3 h-3" /> Decreasing</span>;
      default:
        return <Badge variant="gray" size="xs">{trend || 'Single Log'}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Navigation and Window Toggle */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-[#EFEAF4] shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-[#292431]">PCOSCOPE</h2>
            <Badge variant="purple" size="xs">AI Health Intelligence & Pattern Discovery</Badge>
            {isRefreshing && (
              <span className="flex items-center gap-1 text-xs text-[#7950A8] animate-pulse">
                <RefreshCw className="w-3 h-3 animate-spin" /> Syncing...
              </span>
            )}
          </div>
          <p className="text-xs text-[#77717F] mt-1">
            Analyzing longitudinal relationships across menstrual rhythms, daily symptoms, lifestyle habits, and laboratory biomarkers.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Time Window Selector */}
          <div className="flex items-center p-1 bg-[#FAF9FC] rounded-2xl border border-[#EFEAF4]">
            {[
              { label: '7 Days', val: 7 },
              { label: '30 Days', val: 30 },
              { label: '90 Days', val: 90 },
            ].map(({ label, val }) => (
              <button
                key={val}
                onClick={() => handleWindowChange(val)}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                  windowDays === val
                    ? 'bg-white text-[#7950A8] shadow-xs border border-[#EFEAF4]'
                    : 'text-[#77717F] hover:text-[#292431]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Subtab Pills */}
          <div className="flex items-center p-1 bg-[#FAF9FC] rounded-2xl border border-[#EFEAF4]">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'trends', label: 'Symptom Trends' },
              { id: 'correlations', label: 'Correlations' },
              { id: 'biomarkers', label: 'Biomarkers' },
              { id: 'care-gaps', label: 'Care Gaps' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize transition-all ${
                  activeTab === tab.id
                    ? 'bg-[#7950A8] text-white shadow-xs'
                    : 'text-[#77717F] hover:text-[#292431]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading Skeleton State */}
      {isLoading && (
        <div className="space-y-6 animate-pulse">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="h-44 bg-white rounded-3xl border border-[#EFEAF4] p-6" />
            <div className="h-44 bg-white rounded-3xl border border-[#EFEAF4] p-6" />
            <div className="h-44 bg-white rounded-3xl border border-[#EFEAF4] p-6" />
          </div>
          <div className="h-80 bg-white rounded-3xl border border-[#EFEAF4] p-6" />
        </div>
      )}

      {/* Error & Retry State */}
      {!isLoading && fetchError && (
        <div className="bg-red-50 border border-red-200 rounded-3xl p-6 text-center space-y-3">
          <div className="inline-flex p-3 bg-red-100 text-red-700 rounded-full">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-red-900">Unable to load PCOSCOPE data</h3>
          <p className="text-xs text-red-700 max-w-md mx-auto">{fetchError}</p>
          <button
            onClick={() => fetchPcoscopeData(windowDays)}
            className="px-4 py-2 bg-red-700 text-white text-xs font-bold rounded-xl hover:bg-red-800 transition-all inline-flex items-center gap-2"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Analysis
          </button>
        </div>
      )}

      {/* Loaded Content */}
      {!isLoading && !fetchError && analysis && (
        <>
          {/* Urgent Red Flag Alert Banner (Screened Deterministically) */}
          {analysis.urgent_red_flags?.has_urgent_symptoms && (
            <div className="bg-red-500 text-white p-5 rounded-3xl shadow-sm space-y-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-white animate-bounce" />
                <h4 className="text-sm font-bold tracking-wide">CLINICAL SAFETY ALERT</h4>
              </div>
              <p className="text-xs text-red-100 leading-relaxed">
                {analysis.urgent_red_flags.escalation_message ||
                  'Urgent clinical indicators were identified in your recent entries. Please contact a licensed healthcare professional or seek emergency medical evaluation.'}
              </p>
            </div>
          )}

          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Top 3 KPI Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* 1. Cycle Rhythm & Monash 2023 Regularity */}
                <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-3 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#77717F] uppercase tracking-wider">Menstrual Rhythm</span>
                    <Badge variant={analysis.cycle_patterns.is_irregular ? 'pink' : 'purple'} size="xs">
                      Monash 2023
                    </Badge>
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-[#292431]">
                      {analysis.cycle_patterns.rhythm_classification}
                    </h3>
                    <div className="text-xs text-[#7950A8] font-bold mt-1">
                      {analysis.cycle_patterns.estimated_current_phase}
                    </div>
                    <p className="text-[11px] text-[#77717F] mt-2 leading-relaxed">
                      {analysis.cycle_patterns.sample_size >= 1
                        ? `Average length: ${analysis.cycle_patterns.mean_length_days || '—'} days (±${analysis.cycle_patterns.stdev_days || 0}d variance) across ${analysis.cycle_patterns.sample_size} documented cycles.`
                        : 'No menstrual cycles documented yet.'}
                    </p>
                  </div>

                  {/* Mandatory Ovulation Unconfirmed Disclaimer Badge */}
                  <div className="p-2.5 bg-[#FAF9FC] rounded-xl border border-[#EFEAF4] text-[10px] text-[#77717F] leading-snug">
                    <span className="font-bold text-[#292431]">Ovulation Status:</span> Calendar estimation only. True ovulation confirmation requires mid-luteal serum progesterone, LH surge, or ultrasound tracking.
                  </div>
                </div>

                {/* 2. Data Completeness & Maturity Score */}
                <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-3 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#77717F] uppercase tracking-wider">Profile Completeness</span>
                    <span className="text-xs font-black text-[#7950A8]">
                      {analysis.data_completeness.overall_score_pct}%
                    </span>
                  </div>
                  <div>
                    <div className="w-full bg-[#EDE5F7] h-2.5 rounded-full overflow-hidden">
                      <div
                        className="bg-[#7950A8] h-full rounded-full transition-all duration-500"
                        style={{ width: `${analysis.data_completeness.overall_score_pct}%` }}
                      />
                    </div>
                    <p className="text-xs text-[#292431] font-semibold mt-3">
                      {analysis.data_completeness.recommendation}
                    </p>
                    <div className="grid grid-cols-2 gap-2 mt-2 text-[11px] text-[#77717F]">
                      <span>Cycles: {analysis.data_completeness.cycles_logged_count}</span>
                      <span>Symptoms: {analysis.data_completeness.symptoms_logged_days}d</span>
                      <span>Lifestyle: {analysis.data_completeness.lifestyle_logged_days}d</span>
                      <span>Biomarkers: {analysis.data_completeness.lab_biomarkers_count}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => setIsLogModalOpen(true)}
                    className="w-full py-2 bg-[#FAF9FC] hover:bg-[#EDE5F7] text-[#7950A8] text-xs font-bold rounded-xl border border-[#EFEAF4] transition-all"
                  >
                    + Log Daily Check-In
                  </button>
                </div>

                {/* 3. Clinical Care Gaps Overview */}
                <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-3 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#77717F] uppercase tracking-wider">Care Gaps Identified</span>
                    <Badge variant={analysis.care_gaps.length > 0 ? 'amber' : 'green'} size="xs">
                      {analysis.care_gaps.length} Recommended
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    {analysis.care_gaps.slice(0, 2).map((gap, i) => (
                      <div key={i} className="p-2.5 bg-[#FAF9FC] rounded-xl border border-[#EFEAF4] text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[#292431] line-clamp-1">{gap.title}</span>
                          <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">
                            {gap.priority}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#77717F] line-clamp-1 mt-0.5">{gap.description}</p>
                      </div>
                    ))}
                    {analysis.care_gaps.length === 0 && (
                      <p className="text-xs text-[#77717F] py-4 text-center">
                        All recommended baseline PCOS screenings documented.
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => setActiveTab('care-gaps')}
                    className="w-full py-2 text-[#7950A8] text-xs font-bold hover:underline inline-flex items-center justify-center gap-1"
                  >
                    View All Care Gaps <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* AI Pattern Narrative & Doctor Discussion Points */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* AI Synthesized Observations */}
                <div className="lg:col-span-2 bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-[#7950A8]" />
                      <h3 className="text-sm font-bold text-[#292431]">AI Pattern Synthesis</h3>
                    </div>
                    {insights?.provider_used && (
                      <span className="text-[11px] font-semibold text-[#77717F] bg-[#FAF9FC] px-2 py-1 rounded-md border border-[#EFEAF4]">
                        Provider: {insights.provider_used} ({insights.model_used || 'standard'})
                      </span>
                    )}
                  </div>

                  <div className="text-xs text-[#292431] leading-relaxed whitespace-pre-line bg-[#FAF9FC] p-4 rounded-2xl border border-[#EFEAF4]">
                    {insights?.narrative_summary || (
                      <div className="space-y-2 text-[#77717F]">
                        <p><strong>Menstrual Rhythm:</strong> {analysis.cycle_patterns.rhythm_classification}. {analysis.cycle_patterns.clinical_interpretation}</p>
                        <p><strong>Data Quality:</strong> {analysis.data_completeness.overall_score_pct}% complete. {analysis.data_completeness.recommendation}</p>
                      </div>
                    )}
                  </div>

                  {/* High Priority Key Observations */}
                  {insights?.key_observations?.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-[#77717F] uppercase tracking-wider">Key Observations</h4>
                      <ul className="space-y-1.5 text-xs text-[#292431]">
                        {insights.key_observations.map((obs, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-[#7950A8] mt-1.5 shrink-0" />
                            <span>{obs}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <EthicalDisclaimer title="AI Synthesis Notice">
                    This narrative summary is evidence-grounded decision support derived from your authentic health records. It does not replace individualized clinical evaluation by a licensed healthcare provider.
                  </EthicalDisclaimer>
                </div>

                {/* Doctor Consultation Discussion Points */}
                <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-4 flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Stethoscope className="w-4 h-4 text-[#A6417A]" />
                      <h3 className="text-sm font-bold text-[#292431]">Doctor Discussion Questions</h3>
                    </div>
                    <p className="text-xs text-[#77717F]">
                      High-yield questions tailored to your logged data gaps and symptom patterns for your next visit:
                    </p>

                    <div className="space-y-2.5">
                      {(insights?.doctor_discussion_points || [
                        'Would you recommend assessing fasting insulin or oral glucose tolerance at my next visit?',
                        'Based on my cycle length variance, are further ovulation or hormone checks indicated?',
                        'What evidence-based lifestyle strategies best address my persistent symptom clusters?',
                      ]).map((q, idx) => (
                        <div key={idx} className="p-3 bg-[#FAF9FC] rounded-2xl border border-[#EFEAF4] text-xs text-[#292431] leading-relaxed">
                          <span className="font-bold text-[#A6417A] mr-1.5">{idx + 1}.</span>
                          {q}
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={() => setActiveTab('correlations')}
                    className="w-full py-2.5 bg-[#EDE5F7] text-[#7950A8] font-bold text-xs rounded-2xl border border-[#DFCDEE] hover:bg-[#E3D6F2] transition-all inline-flex items-center justify-center gap-1.5"
                  >
                    View Correlation Matrix <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* SYMPTOM TRENDS TAB */}
          {activeTab === 'trends' && (
            <div className="space-y-6">
              {/* Interactive Recharts Chart Card */}
              <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-bold text-[#292431]">
                      Symptom Temporal Progression (Last {windowDays} Days)
                    </h3>
                    <p className="text-xs text-[#77717F]">Standardized 0–10 clinical severity scale</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-1 bg-[#FAF9FC] p-1 rounded-xl border border-[#EFEAF4] text-[11px]">
                    {[
                      { id: 'all', label: 'All Markers' },
                      { id: 'fatigue', label: 'Fatigue' },
                      { id: 'bloating', label: 'Bloating' },
                      { id: 'pelvic_pain', label: 'Pelvic Pain' },
                      { id: 'acne', label: 'Acne' },
                      { id: 'sleep', label: 'Sleep' },
                    ].map((metric) => (
                      <button
                        key={metric.id}
                        onClick={() => setSelectedMetric(metric.id)}
                        className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                          selectedMetric === metric.id
                            ? 'bg-white text-[#7950A8] shadow-2xs border border-[#EFEAF4]'
                            : 'text-[#77717F] hover:text-[#292431]'
                        }`}
                      >
                        {metric.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Recharts Area/Line Chart */}
                {analysis.symptom_trends.temporal_timeline?.length > 0 ? (
                  <div className="h-72 sm:h-80 w-full pt-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={analysis.symptom_trends.temporal_timeline}
                        margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                      >
                        <defs>
                          <linearGradient id="purpleArea" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#7950A8" stopOpacity={0.25} />
                            <stop offset="95%" stopColor="#7950A8" stopOpacity={0.0} />
                          </linearGradient>
                          <linearGradient id="pinkArea" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#A6417A" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#A6417A" stopOpacity={0.0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F2ECF8" />
                        <XAxis
                          dataKey="date"
                          stroke="#9E98A8"
                          fontSize={11}
                          tickLine={false}
                          tickFormatter={(str) => (str ? str.slice(5) : '')}
                        />
                        <YAxis domain={[0, 10]} stroke="#9E98A8" fontSize={11} tickLine={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#FFFFFF',
                            borderRadius: '16px',
                            border: '1px solid #EFEAF4',
                            boxShadow: '0 8px 24px rgba(41,36,49,0.08)',
                            fontSize: '12px',
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />

                        {(selectedMetric === 'all' || selectedMetric === 'fatigue') && (
                          <Area
                            type="monotone"
                            dataKey="fatigue"
                            name="Fatigue (1-10)"
                            stroke="#7950A8"
                            strokeWidth={2.5}
                            fillOpacity={1}
                            fill="url(#purpleArea)"
                          />
                        )}
                        {(selectedMetric === 'all' || selectedMetric === 'bloating') && (
                          <Line
                            type="monotone"
                            dataKey="bloating"
                            name="Bloating (1-10)"
                            stroke="#D97706"
                            strokeWidth={2}
                            dot={{ r: 2.5 }}
                          />
                        )}
                        {(selectedMetric === 'all' || selectedMetric === 'pelvic_pain') && (
                          <Line
                            type="monotone"
                            dataKey="pelvic_pain"
                            name="Pelvic Pain (1-10)"
                            stroke="#DC2626"
                            strokeWidth={2}
                            strokeDasharray="4 4"
                          />
                        )}
                        {(selectedMetric === 'all' || selectedMetric === 'acne') && (
                          <Line
                            type="monotone"
                            dataKey="acne"
                            name="Acne Score (0-9)"
                            stroke="#A6417A"
                            strokeWidth={2}
                          />
                        )}
                        {(selectedMetric === 'all' || selectedMetric === 'sleep') && (
                          <Line
                            type="monotone"
                            dataKey="sleep_hours"
                            name="Sleep (hrs)"
                            stroke="#0D9488"
                            strokeWidth={2}
                          />
                        )}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="py-16 text-center space-y-3 bg-[#FAF9FC] rounded-2xl border border-dashed border-[#EFEAF4]">
                    <Activity className="w-8 h-8 text-[#9E98A8] mx-auto" />
                    <h4 className="text-sm font-bold text-[#292431]">No Symptom Logs in this Window</h4>
                    <p className="text-xs text-[#77717F] max-w-sm mx-auto">
                      Log daily symptom entries to uncover rolling severity curves and co-occurring hormonal clusters.
                    </p>
                    <button
                      onClick={() => setIsLogModalOpen(true)}
                      className="px-4 py-2 bg-[#7950A8] text-white text-xs font-bold rounded-xl hover:bg-[#684294] transition-all"
                    >
                      + Log First Daily Check-In
                    </button>
                  </div>
                )}
              </div>

              {/* Ranked Symptom Clusters Table */}
              <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-bold text-[#292431]">Ranked Symptom Clusters</h3>
                    <p className="text-xs text-[#77717F]">
                      Identifies symptom prevalence, average severity, and co-occurring symptoms
                    </p>
                  </div>
                  <Badge variant="purple" size="xs">
                    {analysis.symptom_trends.top_clusters.length} Logged Clusters
                  </Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {analysis.symptom_trends.top_clusters.map((cluster, idx) => (
                    <div key={idx} className="p-4 bg-[#FAF9FC] rounded-2xl border border-[#EFEAF4] space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-[#292431]">{cluster.display_name}</span>
                        {getTrendBadge(cluster.trend_direction)}
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-[#77717F]">
                        <div>
                          Prevalence: <strong className="text-[#292431]">{cluster.prevalence_pct}%</strong>
                        </div>
                        <div>
                          Avg Severity: <strong className="text-[#292431]">{cluster.average_severity}/10</strong> ({cluster.severity_label})
                        </div>
                        <div>
                          Logged Days: <strong className="text-[#292431]">{cluster.occurrences_count}</strong>
                        </div>
                        <div>
                          Window: <strong className="text-[#292431]">{cluster.total_window_days}d</strong>
                        </div>
                      </div>
                      {cluster.co_occurring_symptoms?.length > 0 && (
                        <div className="pt-2 border-t border-[#EFEAF4] text-[11px] text-[#77717F]">
                          <span className="font-semibold text-[#292431]">Frequently Co-occurs with:</span>{' '}
                          {cluster.co_occurring_symptoms.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                  {analysis.symptom_trends.top_clusters.length === 0 && (
                    <div className="col-span-full py-8 text-center text-xs text-[#77717F]">
                      No recurring symptom clusters detected in this window.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* CORRELATIONS TAB */}
          {activeTab === 'correlations' && (
            <div className="space-y-6">
              <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-bold text-[#292431]">Lifestyle-Symptom Correlation Matrix</h3>
                    <p className="text-xs text-[#77717F]">
                      Statistical Pearson r associations calculated across paired daily logs
                    </p>
                  </div>
                  <Badge variant="teal" size="sm">N ≥ 7 Minimum Quality Guard</Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {analysis.lifestyle_correlations.map((corr, idx) => (
                    <div
                      key={idx}
                      className={`p-5 rounded-3xl border space-y-3 transition-all ${
                        corr.has_sufficient_data
                          ? 'bg-white border-[#EFEAF4] shadow-xs'
                          : 'bg-[#FAF9FC]/70 border-dashed border-[#E5DEEE]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-[#7950A8]">{corr.factor_a}</span>
                          <span className="text-xs text-[#9E98A8]">↔</span>
                          <span className="text-xs font-bold text-[#292431]">{corr.factor_b}</span>
                        </div>
                        {corr.has_sufficient_data && corr.correlation_coefficient !== null ? (
                          <span className="text-xs font-black px-2.5 py-1 rounded-xl bg-[#EDE5F7] text-[#7950A8] border border-[#DFCDEE]">
                            r = {corr.correlation_coefficient > 0 ? `+${corr.correlation_coefficient}` : corr.correlation_coefficient}
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-200">
                            Insufficient Data
                          </span>
                        )}
                      </div>

                      {/* Sample Size Progress Meter */}
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px] text-[#77717F]">
                          <span>Sample Size (N)</span>
                          <span className="font-bold text-[#292431]">
                            {corr.sample_size} of 7 required days
                          </span>
                        </div>
                        <div className="w-full bg-[#EFEAF4] h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              corr.has_sufficient_data ? 'bg-emerald-500' : 'bg-amber-400'
                            }`}
                            style={{ width: `${Math.min(100, (corr.sample_size / 7) * 100)}%` }}
                          />
                        </div>
                      </div>

                      <p className="text-xs text-[#292431] leading-relaxed">
                        {corr.interpretation}
                      </p>

                      <div className="pt-2 border-t border-[#EFEAF4] text-[10px] text-[#77717F] leading-tight">
                        <strong>Quality Notice:</strong> {corr.significance_warning}
                      </div>
                    </div>
                  ))}
                </div>

                <EthicalDisclaimer title="Observational Correlation vs Medical Causality">
                  Statistical correlation (Pearson r) demonstrates mathematical co-occurrence in your personal logs. It does not establish clinical causality, and external factors like medications, cycle phases, and nutrition must be evaluated with a doctor.
                </EthicalDisclaimer>
              </div>
            </div>
          )}

          {/* BIOMARKERS TAB */}
          {activeTab === 'biomarkers' && (
            <div className="space-y-6">
              <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-bold text-[#292431]">Longitudinal Biomarker Trajectories</h3>
                    <p className="text-xs text-[#77717F]">
                      Tracking sequential blood panel changes against guideline reference intervals
                    </p>
                  </div>
                  <button
                    onClick={() => setIsLabUploadModalOpen(true)}
                    className="px-3.5 py-1.5 bg-[#7950A8] text-white text-xs font-bold rounded-xl hover:bg-[#684294] transition-all inline-flex items-center gap-1.5"
                  >
                    + Upload Lab Report
                  </button>
                </div>

                <div className="space-y-4">
                  {analysis.biomarker_trajectories.map((bio, idx) => (
                    <div key={idx} className="p-4 bg-[#FAF9FC] rounded-2xl border border-[#EFEAF4] space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-[#292431]">{bio.biomarker_name}</h4>
                          <Badge
                            variant={
                              bio.latest_status === 'Normal'
                                ? 'green'
                                : bio.latest_status === 'Elevated'
                                ? 'pink'
                                : 'amber'
                            }
                            size="xs"
                          >
                            {bio.latest_status}
                          </Badge>
                          {getTrendBadge(bio.trajectory_trend)}
                        </div>
                        <div className="text-xs font-bold text-[#292431]">
                          Latest: {bio.latest_value} {bio.latest_unit} ({bio.latest_date || 'Date unrecorded'})
                        </div>
                      </div>

                      <div className="text-xs text-[#77717F] grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <div>
                          Reference Interval: <strong className="text-[#292431]">{bio.reference_interval}</strong>
                        </div>
                        <div>
                          Data Points Recorded: <strong className="text-[#292431]">{bio.datapoints_count}</strong>
                        </div>
                      </div>

                      <p className="text-[11px] text-[#77717F] leading-relaxed">
                        {bio.clinical_significance}
                      </p>

                      {/* Historical Sequential Values */}
                      {bio.history?.length > 1 && (
                        <div className="pt-2 border-t border-[#EFEAF4] flex items-center gap-2 overflow-x-auto text-[11px]">
                          <span className="font-semibold text-[#292431] shrink-0">History:</span>
                          {bio.history.map((h, hIdx) => (
                            <span
                              key={hIdx}
                              className="px-2 py-0.5 rounded bg-white border border-[#EFEAF4] text-[#77717F] shrink-0"
                            >
                              {h.date}: <strong>{h.value}</strong> {h.unit} ({h.status})
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {analysis.biomarker_trajectories.length === 0 && (
                    <div className="py-16 text-center space-y-3 bg-[#FAF9FC] rounded-2xl border border-dashed border-[#EFEAF4]">
                      <FileText className="w-8 h-8 text-[#9E98A8] mx-auto" />
                      <h4 className="text-sm font-bold text-[#292431]">No Lab Biomarkers Stored</h4>
                      <p className="text-xs text-[#77717F] max-w-sm mx-auto">
                        Upload your metabolic and hormone blood tests to track historical trajectories and screen for insulin resistance.
                      </p>
                      <button
                        onClick={() => setIsLabUploadModalOpen(true)}
                        className="px-4 py-2 bg-[#7950A8] text-white text-xs font-bold rounded-xl hover:bg-[#684294] transition-all"
                      >
                        + Upload Blood Test
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* CARE GAPS TAB */}
          {activeTab === 'care-gaps' && (
            <div className="space-y-6">
              <div className="bg-white rounded-3xl border border-[#EFEAF4] p-6 shadow-xs space-y-4">
                <div>
                  <h3 className="text-base font-bold text-[#292431]">Evidence-Based Clinical Care Gaps</h3>
                  <p className="text-xs text-[#77717F]">
                    Identifies missing screenings based on Monash 2023 and Endocrine Society recommendations
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {analysis.care_gaps.map((gap, idx) => (
                    <div key={idx} className="p-5 bg-[#FAF9FC] rounded-3xl border border-[#EFEAF4] space-y-3 flex flex-col justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-[#7950A8] uppercase tracking-wider">
                            {gap.category}
                          </span>
                          <span
                            className={`text-[10px] font-black px-2 py-0.5 rounded-lg ${
                              gap.priority === 'High'
                                ? 'bg-red-50 text-red-700 border border-red-200'
                                : 'bg-amber-50 text-amber-700 border border-amber-200'
                            }`}
                          >
                            {gap.priority} Priority
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-[#292431]">{gap.title}</h4>
                        <p className="text-xs text-[#77717F] leading-relaxed">{gap.description}</p>
                      </div>

                      <div className="pt-2 border-t border-[#EFEAF4] text-[10px] text-[#553878]">
                        <strong>Guideline Reference:</strong> {gap.guideline_source}
                      </div>
                    </div>
                  ))}

                  {analysis.care_gaps.length === 0 && (
                    <div className="col-span-full py-16 text-center space-y-2 bg-[#FAF9FC] rounded-2xl border border-[#EFEAF4]">
                      <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
                      <h4 className="text-sm font-bold text-[#292431]">No Outstanding Care Gaps</h4>
                      <p className="text-xs text-[#77717F]">
                        Your health profile, cycle history, and baseline laboratory panels are fully up to date.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
