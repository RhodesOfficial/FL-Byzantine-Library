"""Readback audit only: no model forwards, gradients, event-method replay or new scores."""
import json
import random
from pathlib import Path
import numpy as np
from direction_b.e01 import ROOT,OUT,LOCAL,load,dump,sha,read_pickle,check_storage
from direction_b.replay import _stratified


def readback():
    manifest=load(OUT/'artifact_hashes.json')
    for item in manifest['files']:
        p=ROOT/item['path']
        assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'], ('saved artifact changed',item['path'])
    progress=load(OUT/'path_progress.json'); summary=load(OUT/'summary.json')
    assert progress['complete_points']==16 and progress['unique_client_evaluations']==320
    assert progress['BN_unchanged'] and len(progress['losses'])==320
    assert len({(v['t'],v['client']) for v in progress['losses']})==320
    inputs=load(OUT/'inputs.json'); D=inputs['D']
    assert inputs['samples']==583 and len(inputs['source_training_hashes'])==5 and inputs['all_parameters_trainable']
    for t in range(16):
        assert (LOCAL/f'theta_t{t:02d}.bin').stat().st_size==4*D
        table=np.load(LOCAL/f'gradient_t{t:02d}.npy',mmap_mode='r')
        assert table.shape==(20,D) and table.dtype==np.float32 and np.isfinite(table).all()
    assert sha(LOCAL/'representative_state.pkl')==load(OUT/'representative.json')['state_sha256']
    rep=read_pickle(LOCAL/'representative_state.pkl'); assert rep['deployment']['t']==1
    final=read_pickle(LOCAL/'rolling_state.pkl')
    deployed=final['deployment']
    assert deployed['t']==16 and deployed['buffer'] is None and not deployed['pending']
    assert deployed['counts']['unique_contributions']==64 and deployed['counts']['tasks_spawned']==80
    assert np.array_equal(deployed['server_seq'],deployed['client_ack'])
    inflight=[a for a in deployed['pending_arrivals'] if a]
    assert len(inflight)==16 and all(a['source']>0 for a in inflight)
    assert not any(k in deployed for k in ('truth','target','error_sum','evaluation_records'))
    # Independent scalar event schedule; no gradient lookup or method execution.
    by_setting={}; main_pairs=[]
    for trajectory in summary['trajectories']:
        records=load(ROOT/trajectory['all_records_path'])
        seed=trajectory['seed']; hetero=trajectory['heterogeneous']; k=trajectory['k']
        rng=[random.Random(seed+1000*i) for i in range(20)]
        tasks=[1]*20
        active={i:((3 if hetero and i%2 else 1)*rng[i].uniform(.9,1.1),0,1) for i in range(20)}
        for t,record in enumerate(records):
            chosen=sorted(active,key=lambda i:(active[i][0],i))[:4]
            actual=record['arrivals']
            assert [a['client'] for a in actual]==chosen and len(set(record['returned_ids']))==4
            assert [a['source'] for a in actual]==[active[i][1] for i in chosen]
            assert [a['task'] for a in actual]==[active[i][2] for i in chosen]
            assert all(a['arrival_time']==active[i][0] for a,i in zip(actual,chosen))
            close=max(active[i][0] for i in chosen)
            for i in chosen:
                del active[i]
                if t<15:
                    tasks[i]+=1
                    active[i]=(close+(3 if hetero and i%2 else 1)*rng[i].uniform(.9,1.1),t+1,tasks[i])
            assert record['counts']['unique_contributions']==4*(t+1)
            assert record['counts']['buffers_consumed']==t+1
            assert record['counts']['rejected_messages']==record['counts']['duplicate_messages']==0
            assert record['arithmetic_reference_difference_squared']<=trajectory['epsilon']
            assert all(source<=t for source in record['sources'])
        assert len(active)==16 and len(records[-1]['terminal_pending'])==16
        assert abs(sum(r['target_squared_norm'] for r in records)/16-trajectory['mean_target_energy'])<=trajectory['epsilon']
        for method,old in trajectory['MSE'].items():
            assert abs(sum(r['errors_squared'][method] for r in records)/16-old)<=trajectory['epsilon']
        if k==1:
            assert all(abs(r['errors_squared']['R']-r['errors_squared']['Ucur'])<=trajectory['epsilon'] and
                       abs(r['errors_squared']['R']-r['errors_squared']['Uhist'])<=trajectory['epsilon'] for r in records)
        key=f"{'hetero' if hetero else 'equal'}_k{k:.2f}"
        group=by_setting.setdefault(key,{'buffers':0,'trajectories':0,'MSE_sums':{},'group_counts':[],
            'gate_enabled':0,'fallback_reasons':{r:0 for r in ('missing_groups','age','residual','norm','unknown')},
            'nonzero_corrections':0,'Uhist_gate_enabled':0,'R_Uhist_gate_disagreements':0,
            'common_eligible_partition_differences':0,'threshold_crossings':0,'common_pair_comparisons':0,
            'even_fast_returns':0,'odd_slow_returns':0,'max_old_age':0})
        group['trajectories']+=1; group['buffers']+=16
        for m,v in trajectory['MSE'].items(): group['MSE_sums'][m]=group['MSE_sums'].get(m,0)+v
        group['nonzero_corrections']+=trajectory['nonzero_corrections']
        for r in records:
            group['group_counts'].append(len(r['partitions']['R']))
            group['gate_enabled']+=int(r['gates']['R']['enabled'])
            group['Uhist_gate_enabled']+=int(r['gates']['Uhist']['enabled'])
            for reason in group['fallback_reasons']:
                group['fallback_reasons'][reason]+=int(bool(r['gates']['R']['reasons'][reason]))
            group['R_Uhist_gate_disagreements']+=int(not r['R_Uhist_gate_equal'])
            group['common_eligible_partition_differences']+=int(not r['group_agreement']['partitions_equal'])
            group['threshold_crossings']+=r['group_agreement']['threshold_crossings']
            group['common_pair_comparisons']+=len(r['group_agreement']['edge_comparisons'])
            group['even_fast_returns']+=sum(i%2==0 for i in r['returned_ids'])
            group['odd_slow_returns']+=sum(i%2==1 for i in r['returned_ids'])
            group['max_old_age']=max(group['max_old_age'],max(r['old_ages']))
        if hetero and k==.1:
            main_pairs.append({'seed':seed,'R_MSE':trajectory['MSE']['R'],
                'C_difference':trajectory['paired_differences']['C'],
                'CACHE_difference':trajectory['paired_differences']['CACHE'],
                'ABS_difference':trajectory['paired_differences']['ABS'],'epsilon':trajectory['epsilon']})
    for group in by_setting.values():
        group['mean_MSE']={m:v/group['trajectories'] for m,v in group.pop('MSE_sums').items()}
        counts=group.pop('group_counts')
        group['group_count_min']=min(counts); group['group_count_max']=max(counts)
        group['group_count_mean']=sum(counts)/len(counts)
        group['group_count_greater_than_B_buffers']=sum(v>4 for v in counts)
    # One new-interface arithmetic fixture, not historical R01 replay or a scientific result.
    d=65537; base=np.zeros(d); base[0]=7; base[-1]=-2
    ua=np.zeros(d); ua[0]=.125
    ub=np.zeros(d); ub[-1]=-.25
    contributions={0:{'u':ua},3:{'u':ub},4:{'u':ub}}
    result=_stratified(base,[[0,1,2],[3,4]],contributions,'u',5)
    expected=base.copy(); expected[0]+=.075; expected[-1]-=.1
    ref_squared=float((result-expected)@(result-expected))
    assert ref_squared<1e-20
    receipts=[]
    for rid in ('e01-001-probe','e01-002-representative','e01-003-restart','e01-004-full-package'):
        p=OUT/'processes'/f'{rid}.json'; r=load(p)
        receipts.append({'run_id':rid,'receipt_sha256':sha(p),'wall_increment':r['external_wall_seconds'],
                         'peak_sampled_OS_working_set':r['sampled_peak_os_process_working_set_bytes'],'exit_code':r['exit_code']})
    dump(OUT/'audit_readback.json',{'task':'B-E01','no_gradients_or_method_buffers_recomputed':True,
        'all_prior_manifest_hashes_and_sizes_verified':True,'manifest_file_count':len(manifest['files']),
        'independent_event_schedule_exact_match_buffers':256,'complete_gradient_objects':320,
        'source_model_bodies_verified':16,'BN_unchanged':True,'encoded_downlink_body_bytes_per_task':4*D,
        'fixed_initial_BN_wire_bytes_per_client':inputs['fixed_BN_wire_bytes'],
        'final_state_t':16,'final_message_pending':0,'final_inflight_tasks_at_horizon':16,
        'total_terminal_inflight_across_16_trajectories':256,'not_additional_expected_buffers':True,
        'final_inflight_sources':[a['source'] for a in inflight],
        'nontrivial_high_dimension_stratified_scalar_reference_squared':ref_squared,
        'main_pairs':main_pairs,'settings':by_setting,'raw_cost_receipts':receipts,
        'prior_unique_wall_seconds_sum':sum(r['wall_increment'] for r in receipts),
        'prior_sampled_peak_working_set':max(r['peak_sampled_OS_working_set'] for r in receipts),
        'scientific_main_conditions':summary['main_comparisons'],
        'scientific_main_nonzero_buffers':summary['main_nonzero_corrections'],
        'scientific_main_numerical_conditions_pass':summary['numerical_main_conditions_pass'],
        'diagnostic_cost_scope':{'unique_full_truth_gradient_table_bytes':395074048,
            'Uhist_extra_float64_cache_object_bytes':20*D*8,
            'Uhist_dense_source_packet_bytes_per_trajectory':79017280,
            'Ucur_generated_dense_payload_same_size_per_return':True,
            'Ucur_bytes_not_transmitted_or_added_to_method_total':True,
            'CPU_cost':'both diagnostics included in measured full Python wall time; per-method CPU attribution not measured',
            'physical_memory':'state object logical sizes not OS or GPU peaks'},
        'artifact_bytes_before_audit_file':check_storage()})
    print(json.dumps({'readback_pass':True,'main_pass':summary['numerical_main_conditions_pass'],
                      'prior_wall_seconds':sum(r['wall_increment'] for r in receipts),'settings':by_setting}),flush=True)


if __name__=='__main__':
    readback()
