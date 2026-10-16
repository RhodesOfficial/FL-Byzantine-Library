"""Not a pytest entry: the metered outer calls this literal-only suite."""


class MappingProbe(dict):
    def __init__(self):
        super().__init__({'cat': 0, 'dog': 1})
        self.visits = 0

    def items(self):
        self.visits += 1
        return super().items()


class SequenceProbe(list):
    def __init__(self, values):
        super().__init__(values)
        self.visits = 0

    def __iter__(self):
        self.visits += 1
        return super().__iter__()


def run_guard_regressions(api):
    b = api.Budget()
    answers = []
    labels = MappingProbe()
    before = b.snapshot()['used']['scans']
    assert api.extract_label_mapping({'label_mapping': labels}, b) == [('cat', 0), ('dog', 1)]
    assert labels.visits == 1 and b.snapshot()['used']['scans'] - before == 1
    answers.append(dict(case='label_mapping', status='PASS', expected_scans=1, observed_visits=1))

    labels = MappingProbe()
    classes = SequenceProbe([{'sources': SequenceProbe([1])}])
    tiny = api.Budget(tiny=dict(read=0, write=0, scans=0))
    for call in (lambda: api.extract_label_mapping({'label_mapping': labels}, tiny),
                 lambda: api.extract_nested_sources(classes, tiny)):
        try:
            call()
        except api.Gate as exc:
            assert 'synthetic local quota' in str(exc)
        else:
            raise AssertionError('expected refusal before collection access')
    assert labels.visits == 0 and classes.visits == 0
    inner = SequenceProbe([1])
    partial = SequenceProbe([{'sources': inner}])
    try:
        api.extract_nested_sources(partial, api.Budget(tiny=dict(read=0, write=0, scans=1)))
    except api.Gate:
        pass
    else:
        raise AssertionError('nested quota refusal absent')
    assert partial.visits == 1 and inner.visits == 0
    answers.append(dict(case='refuse_before_access', status='PASS', label_visits=0,
                        class_visits=0, nested_source_visits=0, charged_class_scan=1))

    left, right = SequenceProbe([1, 2]), SequenceProbe([3])
    classes = SequenceProbe([{'sources': left}, {'sources': right}])
    before = b.snapshot()['used']['scans']
    assert api.extract_nested_sources(classes, b) == [[1, 2], [3]]
    assert (classes.visits, left.visits, right.visits) == (1, 1, 1)
    assert b.snapshot()['used']['scans'] - before == 3
    answers.append(dict(case='nested_manual_operation_table', status='PASS',
                        expected_scans=3, independent_visit_counts=[1, 1, 1]))

    first = b.snapshot()['used']
    replacement = api.Budget()
    assert replacement.snapshot()['used'] == first
    try:
        api.Budget(previous={'used': {'scans': 0}})
    except api.Gate:
        pass
    else:
        raise AssertionError('local reset accepted')
    answers.append(dict(case='restart_subprocess_inheritance', status='PENDING_OUTER_PROBE',
                        replacement_inherits=True, reset_refused=True))

    try:
        raise api.Gate('expected synthetic sealing fixture')
    except api.Gate as injected:
        failure_signature = str(injected)
    fixture = dict(failure_signature=failure_signature, identity='literal-synthetic-guard-fixture-v1', type='InjectedExpectedGate',
                   scientific_results=0, scans_before=b.snapshot()['used']['scans'])
    b.write('failure_fixture.json', fixture)
    import json
    recovered = json.loads(b.read('artifacts/direction_a/phaseG1_3_A_guard_v1/failure_fixture.json'))
    assert recovered == fixture
    answers.append(dict(case='failure_seal_terminal_readback', status='PENDING_OUTER_TERMINAL',
                        failure_fixture_equal=True))
    return dict(identity='literal-synthetic-guard-fixture-v1', cases=answers,
                original_arithmetic_14='NOT_RUN', registered_seed_trajectories=0,
                real_probability_calculations=0, real_gradient_reads=0, formal_events=0,
                real_fee_calculations=0, new_scientific_results=0)
