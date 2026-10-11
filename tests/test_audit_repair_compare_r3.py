from workbench_service.core_product_bff_r1 import CoreProductBFFR1

class Fixture(CoreProductBFFR1):
    def project(self,domain,day):return self.rows[day]

def test_dated_alias_resolution_and_ambiguity_fail_closed():
    obj=Fixture.__new__(Fixture)
    first={'entity_id':'ENTITY1','symbol':'SZ.302132','search_aliases':['','SZ.300114','SZ.302132']}
    second={'entity_id':'ENTITY2','symbol':'SZ.999999','search_aliases':[]}
    obj.rows={'old':[first,second],'absent':[second],'ambiguous':[first,dict(second,search_aliases=['SZ.300114'])]}
    for key in ('300114','302132','SZ.300114','sz.302132','ENTITY1'):
        assert obj.resolve_dated_object('stocks','old',key)['entity_id']=='ENTITY1'
    assert obj.resolve_dated_object('stocks','old','999999')['entity_id']=='ENTITY2'
    for day,key in [('absent','300114'),('ambiguous','300114'),('old','unknown'),('old',''),('old',None)]:
        assert obj.resolve_dated_object('stocks',day,key) is None
