import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  Lightbulb,
  ChevronRight,
  TrendingUp,
  Sparkles,
  AlertCircle,
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Stethoscope,
  Activity,
} from 'lucide-react-native';
import colors from '../../theme/colors';
import typography from '../../theme/typography';
import Header from '../../components/common/Header';
import SegmentedControl from '../../components/common/SegmentedControl';
import SymptomAreaChart from '../../components/charts/SymptomAreaChart';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import EthicalDisclaimer from '../../components/common/EthicalDisclaimer';
import apiClient from '../../services/api';

export default function PcoscopeScreen({ navigation }) {
  const [activeTab, setActiveTab] = useState('Overview');
  const [analysis, setAnalysis] = useState(null);
  const [insights, setInsights] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  const tabs = ['Overview', 'Correlations', 'Trends'];

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setIsRefreshing(true);
    else setIsLoading(true);
    setFetchError(null);

    try {
      const [analysisRes, insightsRes] = await Promise.all([
        apiClient.getPcoscopeAnalysis(30),
        apiClient.getPcoscopeInsights(30).catch(() => null),
      ]);
      setAnalysis(analysisRes);
      setInsights(insightsRes);
    } catch (err) {
      console.warn('PCOSCOPE mobile fetch error:', err);
      setFetchError(err.message || 'Could not connect to PCOSCOPE service.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Map timeline data points for SymptomAreaChart (convert 0-10 scale to 1-5 scale for chart)
  const chartData = (analysis?.symptom_trends?.temporal_timeline || [])
    .slice(-6)
    .map((point) => {
      const dateLabel = point.date ? point.date.slice(5) : 'Day';
      const rawFatigue = Number(point.fatigue || 0);
      const scaledVal = Math.max(1, Math.min(5, Number((rawFatigue / 2).toFixed(1))));
      return {
        label: dateLabel,
        value: scaledVal,
      };
    });

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
      <Header
        showBack
        title="PCOSCOPE"
        subtitle="Pattern Discovery & Health Intelligence"
      />

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={() => loadData(true)}
            colors={[colors.primary]}
          />
        }
      >
        {/* Segmented Tab Bar */}
        <SegmentedControl
          segments={tabs}
          activeSegment={activeTab}
          onChange={setActiveTab}
        />

        {/* Loading State */}
        {isLoading && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loadingText}>Analyzing longitudinal health patterns...</Text>
          </View>
        )}

        {/* Error State */}
        {!isLoading && fetchError && (
          <Card style={styles.errorCard}>
            <AlertCircle size={22} color={colors.danger} />
            <Text style={styles.errorTitle}>Could not load PCOSCOPE data</Text>
            <Text style={styles.errorSubtitle}>{fetchError}</Text>
            <Button
              title="Retry Analysis"
              variant="outline"
              size="small"
              onPress={() => loadData()}
              style={{ marginTop: 8 }}
            />
          </Card>
        )}

        {/* Loaded Content */}
        {!isLoading && !fetchError && analysis && (
          <>
            {/* Urgent Red Flag Alert Banner */}
            {analysis.urgent_red_flags?.has_urgent_symptoms && (
              <Card style={styles.urgentAlertCard}>
                <View style={styles.urgentHeader}>
                  <AlertTriangle size={18} color="#FFFFFF" />
                  <Text style={styles.urgentTitle}>CLINICAL ALERT</Text>
                </View>
                <Text style={styles.urgentText}>
                  {analysis.urgent_red_flags.escalation_message ||
                    'Urgent symptom pattern detected. Please consult a licensed physician immediately.'}
                </Text>
              </Card>
            )}

            {/* TAB: OVERVIEW */}
            {activeTab === 'Overview' && (
              <>
                {/* 1. Cycle Rhythm & Monash Regularity Card */}
                <Card style={styles.cycleCard}>
                  <View style={styles.cardTopRow}>
                    <Text style={styles.categoryLabel}>MENSTRUAL RHYTHM</Text>
                    <Badge
                      label={analysis.cycle_patterns.is_irregular ? 'Irregular' : 'Monash 2023'}
                      variant={analysis.cycle_patterns.is_irregular ? 'warning' : 'primary'}
                      size="small"
                    />
                  </View>

                  <Text style={styles.cardHeading}>
                    {analysis.cycle_patterns.rhythm_classification}
                  </Text>

                  <Text style={styles.estimatedPhaseText}>
                    {analysis.cycle_patterns.estimated_current_phase}
                  </Text>

                  <Text style={styles.cardBodyText}>
                    {analysis.cycle_patterns.sample_size >= 1
                      ? `Average cycle: ${analysis.cycle_patterns.mean_length_days || '—'} days (±${analysis.cycle_patterns.stdev_days || 0}d variance) across ${analysis.cycle_patterns.sample_size} recorded cycles.`
                      : 'No menstrual cycles documented yet. Tracking 3 consecutive cycles unlocks rhythm analysis.'}
                  </Text>

                  {/* Mandatory Ovulation Unconfirmed Disclaimer */}
                  <View style={styles.unconfirmedBox}>
                    <Text style={styles.unconfirmedLabel}>Ovulation Status:</Text>
                    <Text style={styles.unconfirmedText}>
                      Calendar estimation only. Confirmed ovulation requires mid-luteal serum progesterone, LH surge, or ultrasound follicular tracking.
                    </Text>
                  </View>
                </Card>

                {/* 2. Profile Completeness Progress Card */}
                <Card style={styles.completenessCard}>
                  <View style={styles.cardTopRow}>
                    <Text style={styles.categoryLabel}>RECORD MATURITY</Text>
                    <Text style={styles.completenessPct}>
                      {analysis.data_completeness.overall_score_pct}% Complete
                    </Text>
                  </View>

                  <View style={styles.progressBarTrack}>
                    <View
                      style={[
                        styles.progressBarFill,
                        { width: `${analysis.data_completeness.overall_score_pct}%` },
                      ]}
                    />
                  </View>

                  <Text style={styles.completenessRec}>
                    {analysis.data_completeness.recommendation}
                  </Text>

                  <View style={styles.countsRow}>
                    <Text style={styles.countItem}>Cycles: {analysis.data_completeness.cycles_logged_count}</Text>
                    <Text style={styles.countItem}>Symptoms: {analysis.data_completeness.symptoms_logged_days}d</Text>
                    <Text style={styles.countItem}>Lifestyle: {analysis.data_completeness.lifestyle_logged_days}d</Text>
                    <Text style={styles.countItem}>Labs: {analysis.data_completeness.lab_biomarkers_count}</Text>
                  </View>
                </Card>

                {/* 3. AI Key Pattern Insights Card */}
                <Card style={styles.insightsCard}>
                  <View style={styles.insightsHeader}>
                    <View style={styles.lightbulbIcon}>
                      <Sparkles size={16} color={colors.primary} />
                    </View>
                    <Text style={styles.cardHeading}>AI Observed Insights</Text>
                  </View>

                  {/* Dynamic Observations */}
                  {(insights?.key_observations?.length > 0
                    ? insights.key_observations.slice(0, 3)
                    : analysis.symptom_trends.top_clusters.slice(0, 2).map((c) =>
                        `${c.display_name} reported on ${c.prevalence_pct}% of days (avg severity ${c.average_severity}/10, ${c.trend_direction} trend).`
                      )
                  ).map((obs, idx) => (
                    <Pressable
                      key={idx}
                      onPress={() => setActiveTab('Correlations')}
                      style={({ pressed }) => [
                        styles.insightRow,
                        pressed && styles.pressed,
                      ]}
                    >
                      <View style={styles.bulletDot} />
                      <Text style={styles.insightText}>{obs}</Text>
                      <ChevronRight size={16} color={colors.textMuted} />
                    </Pressable>
                  ))}

                  {(!insights?.key_observations || insights.key_observations.length === 0) &&
                    analysis.symptom_trends.top_clusters.length === 0 && (
                      <Text style={styles.emptyCardText}>
                        Log 7 daily check-ins to discover mathematical lifestyle and hormonal patterns.
                      </Text>
                    )}
                </Card>

                {/* 4. Symptom Trend Chart (Live Data) */}
                <Card style={styles.chartCard}>
                  <View style={styles.chartHeader}>
                    <Text style={styles.cardHeading}>Symptom Severity Curve (1-5)</Text>
                    <Badge label="Recent Trend" variant="primary" size="small" />
                  </View>

                  {chartData.length >= 2 ? (
                    <SymptomAreaChart data={chartData} height={160} />
                  ) : (
                    <View style={styles.emptyChartArea}>
                      <Activity size={24} color={colors.textMuted} />
                      <Text style={styles.emptyChartText}>
                        At least 2 daily check-ins required to plot severity curve.
                      </Text>
                    </View>
                  )}

                  <View style={styles.chartFooter}>
                    <Text style={styles.chartFooterText}>
                      {analysis.symptom_trends.summary_note ||
                        'Observational curve describes reported daily symptom severity.'}
                    </Text>
                  </View>
                </Card>

                {/* Doctor Discussion Points Card */}
                {insights?.doctor_discussion_points?.length > 0 && (
                  <Card style={styles.doctorCard}>
                    <View style={styles.doctorHeader}>
                      <Stethoscope size={16} color={colors.secondary} />
                      <Text style={styles.cardHeading}>Doctor Discussion Points</Text>
                    </View>
                    {insights.doctor_discussion_points.slice(0, 3).map((q, qIdx) => (
                      <View key={qIdx} style={styles.questionItem}>
                        <Text style={styles.questionIndex}>{qIdx + 1}.</Text>
                        <Text style={styles.questionText}>{q}</Text>
                      </View>
                    ))}
                  </Card>
                )}

                <EthicalDisclaimer title="Medical Decision Support">
                  PCOSCOPE patterns and statistical calculations are provided for informed discussions with healthcare professionals and do not constitute an automated diagnosis.
                </EthicalDisclaimer>
              </>
            )}

            {/* TAB: CORRELATIONS */}
            {activeTab === 'Correlations' && (
              <View style={styles.correlationsList}>
                <Text style={styles.tabIntroText}>
                  Pearson r correlation matrix with strict N ≥ 7 data-quality threshold:
                </Text>

                {analysis.lifestyle_correlations.map((corr, idx) => (
                  <Card
                    key={idx}
                    style={[
                      styles.corrCard,
                      !corr.has_sufficient_data && styles.insufficientCorrCard,
                    ]}
                  >
                    <View style={styles.corrHeader}>
                      <View style={styles.factorTags}>
                        <Badge label={corr.factor_a} variant="secondary" size="small" />
                        <Text style={styles.corrArrow}>↔</Text>
                        <Badge label={corr.factor_b} variant="primary" size="small" />
                      </View>
                      {corr.has_sufficient_data && corr.correlation_coefficient !== null ? (
                        <Badge
                          label={`r = ${corr.correlation_coefficient > 0 ? '+' : ''}${corr.correlation_coefficient}`}
                          variant={corr.strength === 'Strong' ? 'primary' : 'warning'}
                          size="small"
                        />
                      ) : (
                        <Badge label="N < 7" variant="outline" size="small" />
                      )}
                    </View>

                    {/* Sample Size Progress */}
                    <View style={styles.sampleSizeMeter}>
                      <Text style={styles.sampleSizeText}>
                        Sample Size: <Text style={styles.boldText}>{corr.sample_size}</Text> of 7 required days
                      </Text>
                      <View style={styles.meterTrack}>
                        <View
                          style={[
                            styles.meterFill,
                            {
                              width: `${Math.min(100, (corr.sample_size / 7) * 100)}%`,
                              backgroundColor: corr.has_sufficient_data ? '#10B981' : '#F59E0B',
                            },
                          ]}
                        />
                      </View>
                    </View>

                    <Text style={styles.corrDesc}>{corr.interpretation}</Text>

                    <View style={styles.warningBox}>
                      <Text style={styles.warningText}>{corr.significance_warning}</Text>
                    </View>
                  </Card>
                ))}

                <EthicalDisclaimer title="Non-Causation Notice">
                  Observational statistical correlation does not establish medical causation. Confounding factors such as medications, cycle phase, and diet must be evaluated with your physician.
                </EthicalDisclaimer>
              </View>
            )}

            {/* TAB: TRENDS */}
            {activeTab === 'Trends' && (
              <View style={styles.trendsList}>
                <Text style={styles.tabIntroText}>
                  Ranked symptom clusters and clinical care gaps:
                </Text>

                {/* Symptom Clusters */}
                {analysis.symptom_trends.top_clusters.map((cluster, idx) => (
                  <Card key={idx} style={styles.clusterCard}>
                    <View style={styles.clusterHeader}>
                      <Text style={styles.clusterName}>{cluster.display_name}</Text>
                      <Badge
                        label={`${cluster.trend_direction} Trend`}
                        variant={cluster.trend_direction === 'Increasing' ? 'danger' : 'primary'}
                        size="small"
                      />
                    </View>
                    <View style={styles.clusterMetricsRow}>
                      <Text style={styles.clusterMetric}>
                        Prevalence: <Text style={styles.boldText}>{cluster.prevalence_pct}%</Text>
                      </Text>
                      <Text style={styles.clusterMetric}>
                        Severity: <Text style={styles.boldText}>{cluster.average_severity}/10</Text> ({cluster.severity_label})
                      </Text>
                    </View>
                    {cluster.co_occurring_symptoms?.length > 0 && (
                      <Text style={styles.coOccurText}>
                        Co-occurs with: {cluster.co_occurring_symptoms.join(', ')}
                      </Text>
                    )}
                  </Card>
                ))}

                {analysis.symptom_trends.top_clusters.length === 0 && (
                  <Card style={styles.emptyCard}>
                    <Text style={styles.emptyCardText}>
                      No symptom clusters logged in this window. Log daily check-ins to track recurring hormonal patterns.
                    </Text>
                  </Card>
                )}

                {/* Care Gaps Section */}
                <Text style={[styles.tabIntroText, { marginTop: 16 }]}>
                  Monash 2023 Evidence-Based Care Gaps:
                </Text>

                {analysis.care_gaps.map((gap, gIdx) => (
                  <Card key={gIdx} style={styles.careGapCard}>
                    <View style={styles.careGapTop}>
                      <Text style={styles.careGapCategory}>{gap.category}</Text>
                      <Badge
                        label={`${gap.priority} Priority`}
                        variant={gap.priority === 'High' ? 'danger' : 'warning'}
                        size="small"
                      />
                    </View>
                    <Text style={styles.careGapTitle}>{gap.title}</Text>
                    <Text style={styles.careGapDesc}>{gap.description}</Text>
                    <Text style={styles.careGapSource}>Guideline: {gap.guideline_source}</Text>
                  </Card>
                ))}
              </View>
            )}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    padding: 16,
    gap: 16,
    paddingBottom: 40,
  },
  loadingContainer: {
    padding: 40,
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    ...typography.caption,
    color: colors.textMuted,
  },
  errorCard: {
    padding: 20,
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#FEF2F2',
    borderColor: '#FEE2E2',
  },
  errorTitle: {
    ...typography.h3,
    color: '#991B1B',
    marginTop: 4,
  },
  errorSubtitle: {
    ...typography.caption,
    color: '#B91C1C',
    textAlign: 'center',
  },
  urgentAlertCard: {
    backgroundColor: '#DC2626',
    padding: 16,
    borderColor: '#B91C1C',
    gap: 6,
  },
  urgentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  urgentTitle: {
    ...typography.h3,
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
  urgentText: {
    ...typography.caption,
    color: '#FEE2E2',
    lineHeight: 18,
  },
  cycleCard: {
    padding: 16,
    gap: 8,
  },
  cardTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryLabel: {
    ...typography.caption,
    fontSize: 11,
    fontWeight: '700',
    color: colors.textMuted,
    letterSpacing: 0.5,
  },
  cardHeading: {
    ...typography.h3,
    color: colors.text,
  },
  estimatedPhaseText: {
    ...typography.caption,
    fontSize: 12,
    fontWeight: '700',
    color: colors.primary,
  },
  cardBodyText: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  unconfirmedBox: {
    backgroundColor: colors.surfaceHover || '#FAF9FC',
    padding: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.borderLight,
    marginTop: 4,
  },
  unconfirmedLabel: {
    ...typography.caption,
    fontSize: 11,
    fontWeight: '700',
    color: colors.text,
  },
  unconfirmedText: {
    ...typography.caption,
    fontSize: 10,
    color: colors.textMuted,
    lineHeight: 14,
    marginTop: 2,
  },
  completenessCard: {
    padding: 16,
    gap: 8,
  },
  completenessPct: {
    ...typography.caption,
    fontSize: 12,
    fontWeight: '800',
    color: colors.primary,
  },
  progressBarTrack: {
    height: 6,
    backgroundColor: colors.borderLight,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: colors.primary,
    borderRadius: 3,
  },
  completenessRec: {
    ...typography.bodySmall,
    fontSize: 12,
    fontWeight: '600',
    color: colors.text,
    lineHeight: 16,
  },
  countsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginTop: 4,
  },
  countItem: {
    ...typography.caption,
    fontSize: 11,
    color: colors.textMuted,
  },
  insightsCard: {
    padding: 16,
    gap: 10,
  },
  insightsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  lightbulbIcon: {
    width: 28,
    height: 28,
    borderRadius: 8,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  insightRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    gap: 8,
  },
  bulletDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.primary,
  },
  insightText: {
    ...typography.bodySmall,
    color: colors.text,
    flex: 1,
    lineHeight: 18,
  },
  emptyCardText: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
    paddingVertical: 8,
  },
  chartCard: {
    padding: 16,
  },
  chartHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  emptyChartArea: {
    height: 120,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  emptyChartText: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
  },
  chartFooter: {
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
  },
  chartFooterText: {
    ...typography.caption,
    color: colors.textMuted,
    lineHeight: 16,
  },
  doctorCard: {
    padding: 16,
    gap: 10,
  },
  doctorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  questionItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    paddingVertical: 4,
  },
  questionIndex: {
    ...typography.caption,
    fontSize: 12,
    fontWeight: '700',
    color: colors.secondary,
  },
  questionText: {
    ...typography.caption,
    fontSize: 12,
    color: colors.text,
    flex: 1,
    lineHeight: 17,
  },
  correlationsList: {
    gap: 12,
  },
  tabIntroText: {
    ...typography.caption,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  corrCard: {
    padding: 16,
    gap: 10,
  },
  insufficientCorrCard: {
    backgroundColor: '#FAF9FC',
    borderStyle: 'dashed',
  },
  corrHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  factorTags: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    flexWrap: 'wrap',
    flex: 1,
  },
  corrArrow: {
    ...typography.caption,
    color: colors.textMuted,
  },
  sampleSizeMeter: {
    gap: 4,
  },
  sampleSizeText: {
    ...typography.caption,
    fontSize: 11,
    color: colors.textMuted,
  },
  meterTrack: {
    height: 4,
    backgroundColor: colors.borderLight,
    borderRadius: 2,
    overflow: 'hidden',
  },
  meterFill: {
    height: '100%',
    borderRadius: 2,
  },
  corrDesc: {
    ...typography.bodySmall,
    color: colors.text,
    lineHeight: 18,
  },
  warningBox: {
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
  },
  warningText: {
    ...typography.caption,
    fontSize: 10,
    color: colors.textMuted,
    lineHeight: 14,
  },
  trendsList: {
    gap: 12,
  },
  clusterCard: {
    padding: 16,
    gap: 8,
  },
  clusterHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  clusterName: {
    ...typography.h3,
    fontSize: 14,
    color: colors.text,
  },
  clusterMetricsRow: {
    flexDirection: 'row',
    gap: 16,
  },
  clusterMetric: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  boldText: {
    fontWeight: '700',
    color: colors.text,
  },
  coOccurText: {
    ...typography.caption,
    fontSize: 11,
    color: colors.textMuted,
    paddingTop: 4,
    borderTopWidth: 1,
    borderTopColor: colors.borderLight,
  },
  careGapCard: {
    padding: 16,
    gap: 6,
  },
  careGapTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  careGapCategory: {
    ...typography.caption,
    fontSize: 10,
    fontWeight: '700',
    color: colors.primary,
    letterSpacing: 0.5,
  },
  careGapTitle: {
    ...typography.h3,
    fontSize: 13,
    color: colors.text,
  },
  careGapDesc: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 17,
  },
  careGapSource: {
    ...typography.caption,
    fontSize: 10,
    color: colors.textMuted,
    marginTop: 4,
  },
  emptyCard: {
    padding: 24,
    alignItems: 'center',
  },
  pressed: {
    opacity: 0.7,
  },
});
