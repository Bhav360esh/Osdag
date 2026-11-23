"""
Unit tests for IS800_2025 — covers Stage B (bug fixes) and Stage C (Draft IS 800:2025 additions).

Run from repo root:
    PYTHONPATH=src pytest tests/unit/test_is800_2025.py -v
"""
import sys
import types
import math
import importlib.util
import pytest

# ---------------------------------------------------------------------------
# Lightweight import shim — avoids pulling in the full Osdag GUI / Qt stack
# ---------------------------------------------------------------------------
def _load_is800_2025():
    """Bootstrap IS800_2025 without the full Osdag package tree."""
    _common = types.ModuleType("osdag.Common")
    _common.KEY_Plastic     = "Plastic"
    _common.KEY_Compact     = "Compact"
    _common.KEY_SemiCompact = "Semi-Compact"
    _common.KEY_DP_FAB_SHOP  = "Shop"
    _common.KEY_DP_FAB_FIELD = "Field"
    _common.KEY_DISP_SUPPORT1 = "Simply Supported"
    _common.KEY_DISP_SUPPORT2 = "Cantilever"
    for name in ("osdag", "osdag.utils", "osdag.utils.common"):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules["osdag.Common"] = _common

    spec = importlib.util.spec_from_file_location(
        "osdag.utils.common.is800_2025",
        "src/osdag/utils/common/is800_2025.py",
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "osdag.utils.common"
    spec.loader.exec_module(mod)
    return mod.IS800_2025


IS800_2025 = _load_is800_2025()

GAMMA_M0 = IS800_2025.cl_5_4_1_Table_5["gamma_m0"]["yielding"]       # 1.10
GAMMA_M1 = IS800_2025.cl_5_4_1_Table_5["gamma_m1"]["ultimate_stress"] # 1.25


# ===========================================================================
# STAGE B — Bug Fix Regression Tests
# ===========================================================================

class TestStageBBugFixes:

    # cl_3_8_max_slenderness_ratio
    def test_slenderness_type_1(self):  assert IS800_2025.cl_3_8_max_slenderness_ratio(1) == 180
    def test_slenderness_type_2(self):  assert IS800_2025.cl_3_8_max_slenderness_ratio(2) == 180
    def test_slenderness_type_3(self):  assert IS800_2025.cl_3_8_max_slenderness_ratio(3) == 250
    def test_slenderness_type_4(self):  assert IS800_2025.cl_3_8_max_slenderness_ratio(4) == 300
    def test_slenderness_type_5(self):  assert IS800_2025.cl_3_8_max_slenderness_ratio(5) == 350
    def test_slenderness_type_6(self):  assert IS800_2025.cl_3_8_max_slenderness_ratio(6) == 400
    def test_slenderness_fallback(self): assert IS800_2025.cl_3_8_max_slenderness_ratio(99) == 180

    # cl_8_2_1_2_design_bending_strength
    def test_beta_b_plastic(self):
        Zp, Ze, fy = 1000, 900, 250
        result = IS800_2025.cl_8_2_1_2_design_bending_strength("Plastic", Zp, Ze, fy, GAMMA_M0, "Simply Supported")
        assert abs(result - 1.0 * Zp * fy / GAMMA_M0) < 1e-6

    def test_beta_b_compact(self):
        Zp, Ze, fy = 1000, 900, 250
        result = IS800_2025.cl_8_2_1_2_design_bending_strength("Compact", Zp, Ze, fy, GAMMA_M0, "Simply Supported")
        assert abs(result - 1.0 * Zp * fy / GAMMA_M0) < 1e-6

    def test_beta_b_semi_compact(self):
        Zp, Ze, fy = 1000, 800, 250
        result = IS800_2025.cl_8_2_1_2_design_bending_strength("Semi-Compact", Zp, Ze, fy, GAMMA_M0, "Simply Supported")
        expected = (Ze / Zp) * Zp * fy / GAMMA_M0
        assert abs(result - expected) < 1e-6

    def test_semi_compact_less_than_plastic(self):
        Zp, Ze, fy = 1000, 800, 250
        md_plastic = IS800_2025.cl_8_2_1_2_design_bending_strength("Plastic", Zp, Ze, fy, GAMMA_M0, "Simply Supported")
        md_semi    = IS800_2025.cl_8_2_1_2_design_bending_strength("Semi-Compact", Zp, Ze, fy, GAMMA_M0, "Simply Supported")
        assert md_semi < md_plastic

    # cl_8_2_2_Unsupported_beam_bending_fcrb
    def test_fcrb_formula(self):
        E, Llt_ry, hf_tf = 200000, 60, 10
        expected = (1.1 * math.pi**2 * E / (Llt_ry**2)) * math.sqrt(1 + (Llt_ry/hf_tf)**2 / 20)
        assert abs(IS800_2025.cl_8_2_2_Unsupported_beam_bending_fcrb(E, Llt_ry, hf_tf) - expected) < 1e-6

    def test_fcrb_increases_with_E(self):
        r1 = IS800_2025.cl_8_2_2_Unsupported_beam_bending_fcrb(200000, 50, 8)
        r2 = IS800_2025.cl_8_2_2_Unsupported_beam_bending_fcrb(210000, 50, 8)
        assert r2 > r1

    # cl_9_2_2_high_shear_moment
    def test_high_shear_moment_returns_mdv(self):
        Md, Mfd, b, Ze, fy, gm0 = 500, 400, 0.5, 1000, 250, 1.10
        result = IS800_2025.cl_9_2_2_high_shear_moment(Md, Mfd, b, Ze, fy, gm0)
        expected = Md - b * (Md - Mfd)
        assert abs(result - expected) < 1e-6

    def test_high_shear_moment_b_is_float_no_typeerror(self):
        IS800_2025.cl_9_2_2_high_shear_moment(500, 300, 0.75, 500, 250, 1.10)


# ===========================================================================
# STAGE C — Draft IS 800:2025 Additions
# ===========================================================================

class TestStageCDraftSteelGrades:
    def test_e250(self):
        std, fy, fu = IS800_2025.draft_2025_steel_properties("E250")
        assert std == "IS 2062" and fy == 250.0 and fu == 410.0

    def test_e650(self):
        std, fy, fu = IS800_2025.draft_2025_steel_properties("E650")
        assert fy == 650.0 and fu == 710.0

    def test_fire_resistant(self):
        std, _, _ = IS800_2025.draft_2025_steel_properties("FR_E350")
        assert std == "IS 15103"

    def test_weather_resistant(self):
        std, _, _ = IS800_2025.draft_2025_steel_properties("WR_E250")
        assert std == "IS 11587"

    def test_seismic_resistant(self):
        std, _, _ = IS800_2025.draft_2025_steel_properties("EQ_E350")
        assert std == "IS 15962"

    def test_case_insensitive(self):
        _, fy, _ = IS800_2025.draft_2025_steel_properties("e300")
        assert fy == 300.0

    def test_unknown_grade_raises(self):
        with pytest.raises(ValueError, match="Unsupported or unmapped"):
            IS800_2025.draft_2025_steel_properties("E9999")


class TestStageCWSDRemoval:
    def test_wsd_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="Working Stress Design"):
            IS800_2025.working_stress_design_removed()


class TestStageCTable2iii:
    def test_mid_depth_plastic(self):
        assert IS800_2025.Table2_iii(100, 10, 250, "Neutral axis at mid-depth") == "Plastic"

    def test_mid_depth_slender(self):
        assert IS800_2025.Table2_iii(2000, 10, 250, "Neutral axis at mid-depth") == "Slender"

    def test_generally_missing_axial_load_raises(self):
        with pytest.raises(ValueError):
            IS800_2025.Table2_iii(200, 10, 250, "Generally")

    def test_generally_compression_plastic(self):
        result = IS800_2025.Table2_iii(50, 10, 250, "Generally", axial_load=5000, load_type="compression")
        assert result == "Plastic"

    def test_generally_tension_at_least_as_good(self):
        order = ["Slender", "Semi-Compact", "Compact", "Plastic"]
        rc = IS800_2025.Table2_iii(300, 6, 250, "Generally", axial_load=120000, load_type="compression")
        rt = IS800_2025.Table2_iii(300, 6, 250, "Generally", axial_load=120000, load_type="tension")
        assert order.index(rt) >= order.index(rc)

    def test_axial_compression_slender(self):
        assert IS800_2025.Table2_iii(1000, 10, 250, "Axial compression") == "Slender"

    def test_axial_compression_semi(self):
        assert IS800_2025.Table2_iii(400, 10, 250, "Axial compression") == "Semi-Compact"


class TestStageCTensionRuptureSingleAngle:
    def _p(self):
        return dict(A_nc=900, A_go=950, f_u=410, f_y=250, w=100, t=10, b_s=100, L_c=240)

    def test_positive_T_dn(self):
        assert IS800_2025.cl_6_3_3_tension_rupture_single_angle(**self._p()) > 0

    def test_beta_clamped_at_low_Lc(self):
        p = self._p(); p["L_c"] = 1
        assert IS800_2025.cl_6_3_3_tension_rupture_single_angle(**p) > 0

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError, match="positive"):
            IS800_2025.cl_6_3_3_tension_rupture_single_angle(0, 950, 410, 250, 100, 10, 100, 240)

    def test_T_dn_manual(self):
        A_nc, A_go, f_u, f_y, w, t, b_s, L_c = 500, 400, 410, 250, 50, 6, 75, 150
        beta = max(0.7, min(1.4 - 0.076*(w/t)*(f_y/f_u)*(b_s/L_c), (f_u*GAMMA_M0)/(f_y*GAMMA_M1)))
        expected = (0.9*A_nc*f_u/GAMMA_M1) + (beta*A_go*f_y/GAMMA_M0)
        result = IS800_2025.cl_6_3_3_tension_rupture_single_angle(A_nc, A_go, f_u, f_y, w, t, b_s, L_c)
        assert abs(result - expected) < 1e-6


class TestStageCBucklingClass:
    def test_rolled_I_tf40_hb_gt_1p2(self):
        assert IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(100, 200, 40, "Rolled I-sections") == {"z-z": "a", "y-y": "b"}

    def test_rolled_I_tf41_hb_gt_1p2(self):
        assert IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(100, 200, 41, "Rolled I-sections") == {"z-z": "b", "y-y": "c"}

    def test_rolled_I_tf110(self):
        assert IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(100, 200, 110, "Rolled I-sections") == {"z-z": "d", "y-y": "d"}

    def test_hollow_hot_rolled(self):
        assert IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(100, 100, 8, "Hollow Section", "Hot rolled") == {"z-z": "a", "y-y": "a"}

    def test_hollow_cold_formed(self):
        assert IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(100, 100, 8, "Hollow Section", "Cold formed") == {"z-z": "b", "y-y": "b"}

    def test_welded_box(self):
        assert IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(200, 300, 10, "Welded Box Section") == {"z-z": "b", "y-y": "b"}

    def test_channel_angle_T(self):
        assert IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(100, 100, 8, "Channel, Angle, T and Solid Sections") == {"z-z": "c", "y-y": "c"}

    def test_built_up_member(self):
        assert IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(100, 200, 10, "Built-up Member") == {"z-z": "c", "y-y": "c"}

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown or unsupported"):
            IS800_2025.cl_7_1_2_2_buckling_class_of_crosssections(100, 200, 10, "Magic Section")


class TestStageCConcreteBearing:
    @pytest.mark.parametrize("grade,expected", [
        ("M20", 9.0), ("M55", 24.75), ("M60", 27.0),
        ("M65", 29.25), ("M70", 31.5), ("M75", 33.75), ("M80", 36.0),
    ])
    def test_bearing_strength(self, grade, expected):
        assert abs(IS800_2025.cl_7_4_1_bearing_strength_concrete(grade) - expected) < 1e-9

    def test_case_insensitive(self):
        assert IS800_2025.cl_7_4_1_bearing_strength_concrete("m20") == 9.0

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown or unsupported"):
            IS800_2025.cl_7_4_1_bearing_strength_concrete("M90")


class TestStageCLTBImperfectionFactor:
    def test_rolled(self):    assert IS800_2025.cl_8_2_2_1_ltb_imperfection_factor("Rolled") == 0.21
    def test_rolled_caps(self): assert IS800_2025.cl_8_2_2_1_ltb_imperfection_factor("ROLLED") == 0.21
    def test_welded(self):    assert IS800_2025.cl_8_2_2_1_ltb_imperfection_factor("welded") == 0.49
    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown section_type"):
            IS800_2025.cl_8_2_2_1_ltb_imperfection_factor("Cold formed")


class TestStageCCombinedAxialBending:
    def test_safe(self):
        ratio, is_safe = IS800_2025.cl_9_3_1_1_combined_axial_and_bending_linear(100, 500, 20, 100, 30, 100)
        assert abs(ratio - 0.70) < 1e-9 and is_safe

    def test_unity(self):
        ratio, is_safe = IS800_2025.cl_9_3_1_1_combined_axial_and_bending_linear(100, 100, 0, 100, 0, 100)
        assert ratio == pytest.approx(1.0) and is_safe

    def test_unsafe(self):
        ratio, is_safe = IS800_2025.cl_9_3_1_1_combined_axial_and_bending_linear(400, 500, 80, 100, 80, 100)
        assert ratio > 1.0 and not is_safe

    def test_negative_N_abs(self):
        r_pos, _ = IS800_2025.cl_9_3_1_1_combined_axial_and_bending_linear(200, 400, 50, 100, 0, 100)
        r_neg, _ = IS800_2025.cl_9_3_1_1_combined_axial_and_bending_linear(-200, 400, 50, 100, 0, 100)
        assert abs(r_pos - r_neg) < 1e-9

    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError, match="positive"):
            IS800_2025.cl_9_3_1_1_combined_axial_and_bending_linear(100, 0, 10, 100, 10, 100)


class TestStageCBoltShearCapacity:
    def test_default_field(self):
        assert IS800_2025.cl_10_3_3_bolt_shear_capacity(400, 245, 314, 1, 0, None) > 0

    def test_shop_vs_field_same(self):
        v_s = IS800_2025.cl_10_3_3_bolt_shear_capacity(400, 245, 314, 1, 0, "Shop")
        v_f = IS800_2025.cl_10_3_3_bolt_shear_capacity(400, 245, 314, 1, 0, "Field")
        assert abs(v_s - v_f) < 1e-6

    def test_more_planes_higher_capacity(self):
        v1 = IS800_2025.cl_10_3_3_bolt_shear_capacity(400, 245, 314, 1, 0, "Field")
        v2 = IS800_2025.cl_10_3_3_bolt_shear_capacity(400, 245, 314, 2, 0, "Field")
        assert v2 > v1


class TestStageCBoltSlipResistance:
    def test_standard_kh(self):
        _, K_h, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "Standard")
        assert K_h == 1.0

    def test_oversized_kh(self):
        _, K_h, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "Over-sized")
        assert K_h == 0.85

    def test_short_slot_kh(self):
        _, K_h, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "short_slot")
        assert K_h == 0.85

    def test_long_slot_normal_kh(self):
        for ht in ("long_slot", "long_slot_normal"):
            _, K_h, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, ht)
            assert K_h == 0.85, f"Expected 0.85 for {ht}"

    def test_long_slot_parallel_kh(self):
        _, K_h, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "long_slot_parallel")
        assert K_h == 0.70

    def test_parallel_slot_alias(self):
        _, K_h, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "parallel_slot")
        assert K_h == 0.70

    def test_parallel_less_than_normal(self):
        _, kn, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "long_slot_normal")
        _, kp, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "long_slot_parallel")
        assert kp < kn

    def test_service_load_gamma_lower(self):
        _, _, gm_s = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "Standard", "service_load")
        _, _, gm_u = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.3, "Standard", "ultimate_load")
        assert gm_s < gm_u

    def test_mu_f_cap_at_0p55(self):
        v55, _, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.55, "Standard")
        v60, _, _ = IS800_2025.cl_10_4_3_bolt_slip_resistance(400, 245, 1, 0.60, "Standard")
        assert abs(v55 - v60) < 1e-6
