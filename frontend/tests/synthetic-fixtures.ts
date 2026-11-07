// SYNTHETIC TEST FIXTURES ONLY. Never imported by production source code.
import type { Dataset, Job } from '../src/api/types';
export const datasets:Dataset[]=[{id:'synthetic-demo',name:'SYNTHETIC test network',source:'Synthetic fixture',data_kind:'synthetic',version:'test-v1',periods:[{period:'2025-Q4',validation_status:'valid',node_count:3,edge_count:3},{period:'2025-Q3',validation_status:'valid',node_count:2,edge_count:1}]}];
export const queued:Job={id:'synthetic-test-job',kind:'benchmark',status:'queued',cancel_requested:false,error:null,result:null};
export const financialEligibility={eligible:true,reason:'SYNTHETIC TEST FIXTURE',assumptions:{capital_definition:'fictional book equity'},banks:['A','B','C'].map(id=>({node_id:`SYN-BANK-${id}`,equity:100,external_assets:200,external_liabilities:100,unit:'synthetic units'}))};
