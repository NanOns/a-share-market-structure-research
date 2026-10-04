"""Versioned bridge admission plus the frozen R24R1 algorithm/input consumer."""
from scripts.v4_16_go_forward_input_authority import GoForwardInputAuthority as HistoricalAuthority
from scripts import r25_bridge_oracle_r4r2 as oracle
from types import FunctionType
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_portable_exact import PortableExact

class ImmutableAlgorithmReader:
    """One explicit historical alias, never an authority for the target session."""
    def __init__(self,root,contract):self.root=root;self.contract=contract;self.literal=PortableExact(root)
    def read(self,binding):
        if binding==self.contract['immutable_data_head_predecessor']:
            archived=self.contract['immutable_data_head_readback']
            raw=oracle.exact_bytes(self.root,archived)
            oracle.check(archived['sha256']==binding['sha256'] and archived['bytes']==binding['bytes'],'IMMUTABLE_DATA_ARCHIVE_MISMATCH')
            return raw,dict(role='HISTORICAL_ACCEPTANCE_ONLY',predecessor=binding,explicit_archive=archived)
        return self.literal.read(binding)

class GoForwardInputAuthority(HistoricalAuthority):
    validate_bridge=staticmethod(oracle.inspect_daily_bridge)
    def __init__(self,root,contract_binding,daily_binding,grant,boundary,simulation=False):
        oracle.check(simulation is False,'R4R2_REAL_LOADER_SIMULATION_FORBIDDEN')
        preview=oracle.exact(root,daily_binding)
        self.validate_bridge(root,preview,contract_binding)
        contract=oracle.contract(root,contract_binding)
        factory=lambda root:CurrentStageAuthority(root,exact_reader=ImmutableAlgorithmReader(root,contract))
        # Reuse the frozen constructor bytecode; replace its immutable view only.
        old=HistoricalAuthority.__init__
        constructor=FunctionType(old.__code__,dict(old.__globals__,CurrentStageAuthority=factory),old.__name__,old.__defaults__,old.__closure__)
        constructor(self,root,contract_binding,daily_binding,grant,boundary,simulation=False)
    def bindings(self):
        return dict(super().bindings(),successor_daily_contract=oracle.binding(self.root,oracle.CONTRACT_PATH),
                    immutable_data_head_readback=self.forward_contract['immutable_data_head_readback'])
