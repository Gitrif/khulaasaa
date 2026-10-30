/**
 * Construction Cost & Material Estimator UI controller.
 * Business calculations are owned by services/estimator_service.py (/api/bids/estimate-boq),
 * with immediate client-side sync fallback for responsive input typing.
 */
(function () {
  'use strict';

  let boqFetchTimer = null;

  function switchCalc(tabKey) {
    document.querySelectorAll('.calc-pane').forEach(function (el) {
      el.style.display = 'none';
    });
    document.querySelectorAll('.calc-tab-btn').forEach(function (btn) {
      btn.classList.remove('border-emerald-600', 'text-emerald-800', 'font-bold');
      btn.classList.add('border-transparent', 'text-slate');
    });

    const pane = document.getElementById('pane-' + tabKey);
    const tab = document.getElementById('tab-' + tabKey);
    if (pane) pane.style.display = 'block';
    if (tab) {
      tab.classList.remove('border-transparent', 'text-slate');
      tab.classList.add('border-emerald-600', 'text-emerald-800', 'font-bold');
    }
  }

  function collectBoqInputs() {
    const val = function (id, fallback) {
      const el = document.getElementById(id);
      return el ? el.value : fallback;
    };
    return {
      conc_length: parseFloat(val('concLength', 20)) || 0,
      conc_width: parseFloat(val('concWidth', 15)) || 0,
      conc_thick: parseFloat(val('concThick', 6)) || 0,
      conc_mix: val('concMix', '1:2:4'),
      block_length: parseFloat(val('blockLength', 30)) || 0,
      block_height: parseFloat(val('blockHeight', 10)) || 0,
      block_size: val('blockSize', '6in'),
      plaster_area: parseFloat(val('plasterArea', 600)) || 0,
      plaster_thick: parseFloat(val('plasterThick', 12)) || 12,
      paint_area: parseFloat(val('paintArea', 800)) || 0,
      paint_type: val('paintType', 'interior')
    };
  }

  function applyBoqResult(data) {
    if (!data) return;
    const setTxt = function (id, text) {
      const el = document.getElementById(id);
      if (el) el.innerText = text;
    };
    if (data.concrete) {
      setTxt('concVolume', data.concrete.volume_label);
      setTxt('concCement', data.concrete.cement_bags + ' Bags');
      setTxt('concSand', data.concrete.sand_cuft + ' cu ft');
      setTxt('concAgg', data.concrete.aggregate_cuft + ' cu ft');
    }
    if (data.blocks) {
      setTxt('blockArea', data.blocks.area_sqft + ' sq ft');
      setTxt('blockCount', data.blocks.total_blocks + ' Blocks');
      setTxt('blockCement', data.blocks.mortar_cement_bags + ' Bags');
      setTxt('blockSand', data.blocks.mortar_sand_cuft + ' cu ft');
    }
    if (data.plaster) {
      setTxt('plasterCement', data.plaster.cement_bags + ' Bags');
      setTxt('plasterSand', data.plaster.sand_cuft + ' cu ft');
    }
    if (data.paint) {
      setTxt('paintPrimer', data.paint.primer_litres + ' Litres (≈ ' + data.paint.primer_gallons.toFixed(1) + ' Gallons)');
      setTxt('paintTop', data.paint.top_litres + ' Litres (≈ ' + data.paint.top_gallons.toFixed(1) + ' Gallons)');
    }
    if (data.summary) {
      setTxt('sumCement', data.summary.total_cement_bags + ' Bags');
      setTxt('sumSand', data.summary.total_sand_cuft + ' cu ft');
      setTxt('sumAgg', data.summary.total_aggregate_cuft + ' cu ft');
      setTxt('sumBlocks', data.summary.total_blocks + ' Blocks');
      setTxt('sumCost', data.summary.cost_range_label);
    }
  }

  function requestServerBoqUpdate() {
    if (boqFetchTimer) clearTimeout(boqFetchTimer);
    boqFetchTimer = setTimeout(function () {
      const payload = collectBoqInputs();
      fetch('/api/bids/estimate-boq', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) { if (data) applyBoqResult(data); })
        .catch(function () {});
    }, 80);
  }

  function calculateConcrete() { requestServerBoqUpdate(); }
  function calculateBlocks() { requestServerBoqUpdate(); }
  function calculatePlaster() { requestServerBoqUpdate(); }
  function calculatePaint() { requestServerBoqUpdate(); }
  function updateOverallBOQ() { requestServerBoqUpdate(); }

  window.switchCalc = switchCalc;
  window.calculateConcrete = calculateConcrete;
  window.calculateBlocks = calculateBlocks;
  window.calculatePlaster = calculatePlaster;
  window.calculatePaint = calculatePaint;
  window.updateOverallBOQ = updateOverallBOQ;

  document.addEventListener('DOMContentLoaded', function () {
    requestServerBoqUpdate();
  });
})();
