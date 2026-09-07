from scanner.sector_scanner import scan_row

def test_two_part_breadth_tag(strong):
    strong.update(breadth_ret5_pos_common=.55,breadth_ret20_pos_common=.45,breadth_5_minus_20_common=.10)
    assert scan_row(strong)['breadth_expansion']
    strong['breadth_ret5_pos_common']=.549
    assert not scan_row(strong)['breadth_expansion']
