"""Maldivian Construction & Material BOQ Estimator business service."""
import math
from typing import Any, Dict


def calculate_concrete_boq(
    length_ft: float = 20.0,
    width_ft: float = 15.0,
    thickness_in: float = 6.0,
    mix: str = "1:2:4",
) -> Dict[str, Any]:
    """Calculate concrete volume, cement bags, sand, and aggregate."""
    l_val = max(0.0, float(length_ft or 0.0))
    w_val = max(0.0, float(width_ft or 0.0))
    t_in = max(0.0, float(thickness_in or 0.0))

    wet_vol_cuft = l_val * w_val * (t_in / 12.0)
    wet_vol_cum = wet_vol_cuft * 0.0283168
    dry_vol_cuft = wet_vol_cuft * 1.54

    c_ratio, s_ratio, a_ratio = 1.0, 2.0, 4.0
    if mix == "1:1.5:3":
        c_ratio, s_ratio, a_ratio = 1.0, 1.5, 3.0
    elif mix == "1:3:6":
        c_ratio, s_ratio, a_ratio = 1.0, 3.0, 6.0

    sum_ratio = c_ratio + s_ratio + a_ratio
    cement_cuft = (c_ratio / sum_ratio) * dry_vol_cuft
    cement_bags = int(math.ceil(cement_cuft / 1.25)) if wet_vol_cuft > 0 else 0
    sand_cuft = int(round((s_ratio / sum_ratio) * dry_vol_cuft))
    agg_cuft = int(round((a_ratio / sum_ratio) * dry_vol_cuft))

    return {
        "wet_volume_cuft": round(wet_vol_cuft, 1),
        "wet_volume_cum": round(wet_vol_cum, 2),
        "volume_label": f"{wet_vol_cuft:.1f} cu ft ({wet_vol_cum:.2f} cu m)",
        "cement_bags": cement_bags,
        "sand_cuft": sand_cuft,
        "aggregate_cuft": agg_cuft,
    }


def calculate_blocks_boq(
    length_ft: float = 30.0,
    height_ft: float = 10.0,
    block_size: str = "6in",
) -> Dict[str, Any]:
    """Calculate hollow/solid block count and mortar requirements."""
    l_val = max(0.0, float(length_ft or 0.0))
    h_val = max(0.0, float(height_ft or 0.0))
    area_sqft = l_val * h_val

    base_blocks = area_sqft * 1.125
    total_blocks = int(math.ceil(base_blocks * 1.05)) if area_sqft > 0 else 0

    mortar_factor = 0.014
    sand_factor = 0.055
    if block_size == "8in":
        mortar_factor = 0.018
        sand_factor = 0.070
    elif block_size == "4in":
        mortar_factor = 0.011
        sand_factor = 0.042

    mortar_cement = round(total_blocks * mortar_factor, 1)
    mortar_sand = int(round(total_blocks * sand_factor))

    return {
        "area_sqft": round(area_sqft, 1),
        "total_blocks": total_blocks,
        "mortar_cement_bags": mortar_cement,
        "mortar_sand_cuft": mortar_sand,
    }


def calculate_plaster_boq(
    area_sqft: float = 600.0,
    thickness_mm: float = 12.0,
) -> Dict[str, Any]:
    """Calculate wall plastering cement and sand."""
    area = max(0.0, float(area_sqft or 0.0))
    thick_mm = max(1.0, float(thickness_mm or 12.0))

    thick_ft = (thick_mm / 25.4) / 12.0
    vol_cuft = area * thick_ft * 1.3
    cement_bags = max(1, int(math.ceil(vol_cuft * 0.22))) if area > 0 else 0
    sand_cuft = int(round(vol_cuft * 0.9))

    return {
        "area_sqft": round(area, 1),
        "thickness_mm": thick_mm,
        "cement_bags": cement_bags,
        "sand_cuft": sand_cuft,
    }


def calculate_paint_boq(
    area_sqft: float = 800.0,
    paint_type: str = "interior",
) -> Dict[str, Any]:
    """Calculate primer and top-coat paint volume in litres and gallons."""
    area = max(0.0, float(area_sqft or 0.0))
    primer_coverage = 90.0 if paint_type == "exterior" else 100.0
    top_coverage = 90.0 if paint_type == "exterior" else 100.0

    primer_litres = int(math.ceil(area / primer_coverage)) if area > 0 else 0
    top_litres = int(math.ceil((area * 2.0) / top_coverage)) if area > 0 else 0

    return {
        "area_sqft": round(area, 1),
        "primer_litres": primer_litres,
        "primer_gallons": round(primer_litres / 4.0, 1),
        "top_litres": top_litres,
        "top_gallons": round(top_litres / 4.0, 1),
        "total_paint_litres": primer_litres + top_litres,
    }


def calculate_full_boq(params: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate complete Maldivian construction material & MVR cost estimate."""
    concrete = calculate_concrete_boq(
        length_ft=params.get("conc_length", 20.0),
        width_ft=params.get("conc_width", 15.0),
        thickness_in=params.get("conc_thick", 6.0),
        mix=str(params.get("conc_mix", "1:2:4")),
    )
    blocks = calculate_blocks_boq(
        length_ft=params.get("block_length", 30.0),
        height_ft=params.get("block_height", 10.0),
        block_size=str(params.get("block_size", "6in")),
    )
    plaster = calculate_plaster_boq(
        area_sqft=params.get("plaster_area", 600.0),
        thickness_mm=params.get("plaster_thick", 12.0),
    )
    paint = calculate_paint_boq(
        area_sqft=params.get("paint_area", 800.0),
        paint_type=str(params.get("paint_type", "interior")),
    )

    total_cement = int(
        math.ceil(
            concrete["cement_bags"]
            + blocks["mortar_cement_bags"]
            + plaster["cement_bags"]
        )
    )
    total_sand = (
        concrete["sand_cuft"] + blocks["mortar_sand_cuft"] + plaster["sand_cuft"]
    )
    total_agg = concrete["aggregate_cuft"]
    total_blocks = blocks["total_blocks"]
    total_paint_litres = paint["total_paint_litres"]

    est_min_mvr = int(
        round(
            total_cement * 115
            + total_sand * 28
            + total_agg * 42
            + total_blocks * 14
        )
    )
    est_max_mvr = int(
        round(
            total_cement * 135
            + total_sand * 35
            + total_agg * 52
            + total_blocks * 17
        )
    )

    return {
        "concrete": concrete,
        "blocks": blocks,
        "plaster": plaster,
        "paint": paint,
        "summary": {
            "total_cement_bags": total_cement,
            "total_sand_cuft": total_sand,
            "total_aggregate_cuft": total_agg,
            "total_blocks": total_blocks,
            "total_paint_litres": total_paint_litres,
            "est_min_mvr": est_min_mvr,
            "est_max_mvr": est_max_mvr,
            "cost_range_label": f"MVR {est_min_mvr:,} – {est_max_mvr:,}",
        },
    }
