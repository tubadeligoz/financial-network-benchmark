export type AlgorithmId = 'strength' | 'betweenness' | 'pagerank' | 'debtrank';
export type Page = 'datasets' | 'explorer' | 'benchmarks' | 'results';
export interface GraphIdentity {
  dataset_id: string; dataset_version: string; selected_period: string; graph_sha256: string;
  data_kind: string; node_count: number; edge_count: number; density: number;
  direction: string; exposure_unit: string; creditor_scope: string; debtor_scope: string;
}
export interface Period extends Partial<GraphIdentity> { period: string; validation_status: string; warning_count?: number; error?: string }
export interface Dataset { id: string; name: string; source: string; data_kind: string; version: string; periods: Period[] }
export interface Score { node_id: string; score: number; rank: number; metrics: Record<string, number> }
export interface AlgorithmResult {
  algorithm_id: AlgorithmId; algorithm_name: string; algorithm_version: string; dataset_id: string;
  dataset_version: string; period: string; graph_sha256: string; status: string; parameters: Record<string, unknown>;
  scores: Score[]; metadata: Record<string, unknown> & {scenario?: RiskScenario;seed_scenarios?:Record<string,RiskScenario>;model_id?:string;model_assumptions?:Record<string,string>;analysis_objective?:string}; node_count?: number; constant_scores?: boolean;
  experiment_id?:string;
}
export interface NodeStats { in_degree: number; out_degree: number; in_strength: number; out_strength: number }
export interface GraphNode extends NodeStats { id: string; label: string; name: string }
export interface GraphEdge { id: string; source: string; target: string; exposure: number }
export interface GraphView {
  graph_sha256: string; period: string; total_nodes: number; total_edges: number; visible_nodes: number;
  visible_edges: number; filtered: boolean; filter_description: string; exposure_unit: string;
  analysis_scope: string; nodes: GraphNode[]; edges: GraphEdge[];
}
export interface NodeDetail {
  node_id: string; attributes: { entity_type: string; source_metadata?: { country_name?: string } };
  statistics: NodeStats; scores: Partial<Record<AlgorithmId, number>>; neighbors: string[];
  connections: { source: string; target: string; exposure: number }[]; total_connections: number; exposure_unit: string;
}
export interface SummaryStats { count: number; mean: number | null; median: number | null; standard_deviation: number | null; min: number | null; max: number | null }
export interface Aggregate {
  runtime_seconds: SummaryStats; sampled_peak_rss_bytes: SummaryStats; process_peak_rss_bytes: SummaryStats;
  timing_successes: number; memory_successes: number; timing_complete: boolean; memory_complete: boolean;
  status_counts: Record<string, number>; ranking_repeatable: boolean | null;
}
export interface Experiment {
  id: string; experiment_id: string; run_id: string; status: string; graph: GraphIdentity;
  aggregated: Record<string, Aggregate>; algorithm_cases: { case_id: string; algorithm_id: AlgorithmId; parameters: Record<string, unknown> }[];
  comparison_exclusions?:{left_case:string;right_case:string;reason:string}[];
}
export interface Comparison {
  left_case: string; right_case: string; node_count: number; spearman: number | null;
  top_k: { k: number; overlap: number | null; jaccard: number | null; left_cutoff_tie?: boolean; right_cutoff_tie?: boolean }[];
}
export interface ExperimentResults {
  id: string; summary: Experiment; rankings: Record<string, AlgorithmResult>; comparisons: Comparison[];
  dataset_key: string | null; environment: { packages: Record<string, string>; benchmark_version: string };
}
export interface Job {
  id: string; kind: string; status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  cancel_requested: boolean; error: string | { message?: string } | null;
  result: { experiment_id?: string; run_id?: string; analysis?: AlgorithmResult;stress_experiment_id?:string } | null;
  progress?: { message: string; completed: number | null; total: number | null } | null;
}
export interface Case { case_id: string; algorithm_id: AlgorithmId; parameters: Record<string, unknown> }
export interface ScaleRow { experiment_id: string; dataset: string; node_count: number; edge_count: number; case_id: string; median_seconds: number | null; timing_successes: number; status: string }
export interface Temporal { pairs: { left_period: string; right_period: string; left_density: number; right_density: number; cases: { case_id: string; comparison: Comparison & { left_only_nodes: string[]; right_only_nodes: string[] } }[] }[] }
export interface RiskScenario {
  initial_shocks:Record<string,number>;affected_nodes:string[];final_distress:Record<string,number>;
  economic_value_weights:Record<string,number>;aggregate_initial_distress:number;aggregate_distress:number;
  debtrank_score:number;steps:number;stopping_reason:string;
  history:{step:number;distress:Record<string,number>;states:Record<string,string>;transmissions:{source:string;target:string;exposure_source:string;exposure_target:string;potential_distress_increment:number}[]}[];
}
export interface RiskOverlay {scenario:RiskScenario;step:number}
export interface StressSuite {id:string;experiment_id:string;dataset_key:string;status:string;label:string;scenarios:AlgorithmResult[];impact_rankings:AlgorithmResult[]}
export interface FinancialEligibility {eligible:boolean;reason:string;assumptions:Record<string,string>|null;banks:{node_id:string;equity:number;external_assets:number;external_liabilities:number;unit:string}[]}
