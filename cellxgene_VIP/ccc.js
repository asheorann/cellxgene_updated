//=============================================================================
// Cell-Cell Communication (CCC) Tab Functions
//
// Loaded by the one-line hook at the end of interface.html. Adds the CCC tab
// button and the tab content (ccc.html) so VIP's own files stay unmodified.
// See CHANGES_FROM_UPSTREAM.md.
//=============================================================================

(function(){
  var base = window.location.href.replace(/\/+$/,'') + '/static/';
  $.get(base + 'ccc.html', function(html){
    var btn = $('<button class="tablinks">CCC: Cell Communication</button>').on('click', function(event){
      selFun(event, 'CCC');
      CCCinit();
    });
    var hr = '<hr size="1" noshade>';
    var cliBtn = $('button.tablinks').filter(function(){
      return ($(this).attr('onclick') || '').indexOf("'CLI'") >= 0;
    });
    if(cliBtn.length){
      cliBtn.first().before($(hr), btn, $(hr));
    } else {
      $('button.tablinks').last().after($(hr), btn);
    }
    if($('#CLI.tabcontent').length){
      $('#CLI.tabcontent').before(html);
    } else {
      $('.tabcontent').last().after(html);
    }
  }).fail(function(){
    console.error("CCC: could not load " + base + "ccc.html");
  });
})();

// Lasso mode: Selection 1 is the sender unless swapped
var CCClassoSwapped = false;

// Toggle targeted/untargeted mode visibility
$(document).on('change', 'input[name="CCCmode"]', function(){
  var mode = $('input[name="CCCmode"]:checked').val();
  if(mode === "targeted"){
    $("#CCCtargetedOptions").show();
  } else {
    $("#CCCtargetedOptions").hide();
  }
  CCCupdateSRSource();
});
$(document).on('change', 'input[name="CCCsrcSource"]', CCCupdateSRSource);

function CCClassoActive(){
  return $('input[name="CCCmode"]:checked').val() === "targeted" &&
         $('input[name="CCCsrcSource"]:checked').val() === "lasso";
}

// Show annotation dropdowns or lasso selections for sender/receiver
function CCCupdateSRSource(){
  var lasso = CCClassoActive();
  $("#CCCannotationSR").toggle(!lasso);
  $("#CCClassoSR").toggle(lasso);
  // Lasso selections define the groups, so these don't apply
  $("#CCCcellsRow").toggle(!lasso);
  $("#CCCgroupbyRow").toggle(!lasso);
  CCCrenderLassoSR();
}

function CCClassoNames(){
  return CCClassoSwapped ? ["Selection 2", "Selection 1"] : ["Selection 1", "Selection 2"];
}

function CCCrenderLassoSR(){
  // cellN spans are kept current by cellNupdate()
  var span = function(name){
    var cls = name === "Selection 1" ? "cellN1" : "cellN2";
    var n = $('.'+cls).first().text() || 0;
    return name + ' (<span class="'+cls+'" style="color:red;">'+n+'</span> cells)';
  };
  var names = CCClassoNames();
  $("#CCClassoSender").html(span(names[0]));
  $("#CCClassoReceiver").html(span(names[1]));
  if(CCClassoActive() && $("#CCCcompareBy").val()) CCCupdatePreview();
}

// Store the current lasso as the sender (role 0) or receiver (role 1) selection,
// same as clicking the 1/2 cell set buttons in the cellxgene menubar
function CCCsetFromLasso(role){
  var selected = window.store.getState().obsCrossfilter.allSelectedLabels();
  if(selected.length === 0 || selected.length === window.store.getState().annoMatrix.nObs){
    alert("Lasso some cells on the plot first");
    return;
  }
  var setId = CCClassoNames()[role].slice(-1);
  window.store.dispatch({type: "store current cell selection as differential set "+setId, data: selected});
  cellNupdate();
  CCCrenderLassoSR();
}

function CCCswapSR(){
  if(CCClassoActive()){
    CCClassoSwapped = !CCClassoSwapped;
    CCCrenderLassoSR();
    return;
  }
  var s = $("#CCCsender").val();
  $("#CCCsender").val($("#CCCreceiver").val());
  $("#CCCreceiver").val(s);
}

// Update sender/receiver dropdowns when groupby changes
function CCCupdateSenderReceiver(){
  var grpKey = $("#CCCgroupby option:selected").val();
  if(!grpKey || grpKey === "NA") return;

  var grpL = window.store.getState().annoMatrix.schema.annotations.obsByName;
  if(!grpL[grpKey]) return;

  var categories = grpL[grpKey].categories;

  // Clear and populate sender/receiver dropdowns
  $("#CCCsender").empty();
  $("#CCCreceiver").empty();

  for(var i = 0; i < categories.length; i++){
    var cat = categories[i];
    if(cat === null) cat = "NA";
    $("#CCCsender").append('<option value="'+cat+'">'+cat+'</option>');
    $("#CCCreceiver").append('<option value="'+cat+'">'+cat+'</option>');
  }

  // Select different defaults if possible
  if(categories.length > 1){
    $("#CCCreceiver").val(categories[1]);
  }
}

//-----------------------------------------------------------------------------
// Comparison view (two conditions, absolute values across replicates)
//-----------------------------------------------------------------------------

function CCCesc(x){ return $('<div>').text(x === undefined || x === null ? '' : String(x)).html(); }

// Show the comparison controls and fill reference/test/replicate dropdowns,
// keeping the current choices when still valid
function CCCupdateCompare(){
  var compareBy = $("#CCCcompareBy").val();
  var on = !!compareBy;
  $("#CCCcompareOptions").toggle(on);
  // Rank-based options only apply to the single-condition view
  $("#CCCmethod, #CCCnPerms, #CCCsortBy").prop('disabled', on);
  if(!on){
    $("#CCCpreview").html("");
    return;
  }
  var grpL = window.store.getState().annoMatrix.schema.annotations.obsByName;
  if(!grpL[compareBy]) return;
  var cats = (grpL[compareBy].categories || []).map(function(c){ return c === null ? "NA" : String(c); });
  var prevRef = $("#CCCref").val(), prevTest = $("#CCCtest").val(), prevSample = $("#CCCsample").val();
  $("#CCCref, #CCCtest").empty();
  cats.forEach(function(c){
    $("#CCCref").append($('<option>').val(c).text(c));
    $("#CCCtest").append($('<option>').val(c).text(c));
  });
  $("#CCCref").val(cats.indexOf(prevRef) >= 0 ? prevRef : cats[0]);
  $("#CCCtest").val(cats.indexOf(prevTest) >= 0 ? prevTest : (cats[1] || cats[0]));

  $("#CCCsample").empty().append('<option value="">None: pool cells (descriptive only)</option>');
  for(var key in grpL){
    if(key !== compareBy && grpL[key].categories && grpL[key].categories.length > 1){
      $("#CCCsample").append($('<option>').val(key).text(key));
    }
  }
  if(prevSample && grpL[prevSample] && prevSample !== compareBy) $("#CCCsample").val(prevSample);
  CCCloadLayers();
  CCCupdatePreview();
}

// Expression layers and their normalization checks, from the server (once per page)
var CCClayers = null;
function CCCloadLayers(){
  if(CCClayers) return;
  $("#CCClayerStatus").text("checking layers...").css('color', '#666');
  $.ajax({
    type: "POST",
    url: VIPurl,
    data: JSON.stringify({method: "CCC", action: "layers"}),
    contentType: 'application/json;charset=UTF-8',
    success: function(res){
      var d;
      try { d = JSON.parse(res); } catch(e) {
        $("#CCClayerStatus").text("Could not check expression layers").css('color', 'red');
        return;
      }
      CCClayers = d.layers;
      var sel = $("#CCClayer").empty();
      sel.append($('<option>').val('auto').text('Auto (' + (d.auto || 'none usable') + ')'));
      d.layers.forEach(function(l){
        sel.append($('<option>').val(l.key).attr('title', l.message)
                     .text(l.key + (l.status === 'fail' ? ' (not usable)' : ''))
                     .prop('disabled', l.status === 'fail'));
      });
      CCCshowLayerStatus();
    },
    error: function(){ $("#CCClayerStatus").text("Could not check expression layers").css('color', 'red'); }
  });
}

function CCCshowLayerStatus(){
  if(!CCClayers) return;
  var key = $("#CCClayer").val();
  if(key === 'auto') key = (CCClayers.find(function(l){ return l.status !== 'fail'; }) || {}).key;
  var l = CCClayers.find(function(x){ return x.key === key; });
  var colours = {ok: '#2e7d32', warn: '#c25e00', fail: 'red'};
  $("#CCClayerStatus").text(l ? l.key + ': ' + l.message : 'No log-normalized expression layer found')
                      .css('color', l ? colours[l.status] : 'red');
}

// Before running: replicates per condition with enough cells, as the server will
// count them (block below 2 mice, warn below 3). Sets CCCpreviewBlock when the
// targeted comparison can't run.
var CCCpreviewBlock = null;
function CCCupdatePreview(){
  CCCpreviewBlock = null;
  var compareBy = $("#CCCcompareBy").val();
  if(!compareBy) return;
  var ref = $("#CCCref").val(), test = $("#CCCtest").val(), sampleKey = $("#CCCsample").val();
  var minCells = parseInt($("#CCCminCellsSample").val()) || 30;
  var lasso = CCClassoActive(), groupby = $("#CCCgroupby").val();
  var targeted = $('input[name="CCCmode"]:checked').val() === "targeted";
  if(ref === test){
    CCCpreviewBlock = "Reference and test conditions must differ";
    $("#CCCpreview").html('<span style="color:red;">' + CCCpreviewBlock + '.</span>');
    return;
  }
  if(!lasso && (!groupby || groupby === "NA")){
    $("#CCCpreview").html('<i>Pick a cell type annotation to see replicate counts.</i>');
    return;
  }
  var cols = [compareBy].concat(lasso ? [] : [groupby]).concat(sampleKey ? [sampleKey] : []);
  var annoMatrix = window.store.getState().annoMatrix;
  $("#CCCpreview").html('<i>Counting replicates...</i>');
  Promise.all(cols.map(function(c){ return annoMatrix.fetch("obs", c); })).then(function(dfs){
    var get = function(i){ return dfs[i].col(cols[i]).asArray(); };
    var cond = get(0), type;
    if(lasso){
      var sel = getCells(null, true);
      var s1 = new Set(sel['celllist1'] || []), s2 = new Set(sel['celllist2'] || []);
      type = new Array(cond.length).fill(null);
      s1.forEach(function(i){ if(!s2.has(i)) type[i] = "Selection 1"; });
      s2.forEach(function(i){ if(!s1.has(i)) type[i] = "Selection 2"; });
    } else {
      type = get(1);
    }
    var sample = sampleKey ? get(cols.length - 1) : cond;

    // counts[condition][replicate][cell type], and which conditions each replicate is in
    var counts = {}, repConds = {};
    counts[ref] = {}; counts[test] = {};
    for(var i = 0; i < cond.length; i++){
      var c = String(cond[i]);
      if((c !== ref && c !== test) || type[i] === null) continue;
      var smp = String(sample[i]), t = String(type[i]);
      counts[c][smp] = counts[c][smp] || {};
      counts[c][smp][t] = (counts[c][smp][t] || 0) + 1;
      repConds[smp] = repConds[smp] || {};
      repConds[smp][c] = true;
    }
    var mixed = Object.keys(repConds).filter(function(r){ return Object.keys(repConds[r]).length > 1; });
    if(sampleKey && mixed.length){
      CCCpreviewBlock = "Each replicate must belong to one condition; in both: " + mixed.slice(0, 8).join(", ");
      $("#CCCpreview").html('<span style="color:red;">' + CCCesc(CCCpreviewBlock) + '</span>');
      return;
    }

    var minReps = sampleKey ? 2 : 1;
    var unit = sampleKey ? "mice" : "pooled";
    var cellFor = function(n, total){
      if(n < minReps) return '<td style="color:red; padding:2px 8px;">' + (sampleKey ? n + ' of ' + total + ' ✗' : '✗ &lt; ' + minCells + ' cells') + '</td>';
      if(sampleKey && n < 3) return '<td style="color:#c25e00; padding:2px 8px;">' + n + ' of ' + total + ' ⚠</td>';
      return '<td style="color:#2e7d32; padding:2px 8px;">' + (sampleKey ? n + ' of ' + total + ' ✓' : '✓') + '</td>';
    };
    var qualify = function(c, a, b){
      return Object.keys(counts[c]).filter(function(smp){
        return (counts[c][smp][a] || 0) >= minCells && (counts[c][smp][b] || 0) >= minCells;
      }).length;
    };
    var head = '<tr><th></th><th style="padding:2px 8px;">' + CCCesc(ref) + ' (ref)</th><th style="padding:2px 8px;">' + CCCesc(test) + ' (test)</th></tr>';
    var html = '<table style="border-collapse:collapse;">' + head, blocked = [];
    if(targeted){
      var names = lasso ? CCClassoNames() : [$("#CCCsender").val(), $("#CCCreceiver").val()];
      var pairs = [[names[0], names[1]]];
      if($('input[name="CCCdirection"]:checked').val() === "both_ways" && names[0] !== names[1]) pairs.push([names[1], names[0]]);
      pairs.forEach(function(p){
        html += '<tr><td style="padding:2px 8px;">' + CCCesc(p[0]) + ' → ' + CCCesc(p[1]) + '</td>';
        [ref, test].forEach(function(c){
          var n = qualify(c, p[0], p[1]);
          if(n < minReps) blocked.push(c);
          html += cellFor(n, Object.keys(counts[c]).length);
        });
        html += '</tr>';
      });
    } else {
      var types = {};
      [ref, test].forEach(function(c){ Object.keys(counts[c]).forEach(function(smp){ Object.keys(counts[c][smp]).forEach(function(t){ types[t] = 1; }); }); });
      Object.keys(types).sort().forEach(function(t){
        html += '<tr><td style="padding:2px 8px;">' + CCCesc(t) + '</td>';
        [ref, test].forEach(function(c){ html += cellFor(qualify(c, t, t), Object.keys(counts[c]).length); });
        html += '</tr>';
      });
    }
    html += '</table><small style="color:#666;">' + (sampleKey ? 'Mice' : 'Conditions') + ' with &ge; ' + minCells +
            ' cells of ' + (targeted ? 'both sender and receiver' : 'the cell type (a pair needs both)') + '. ' +
            (sampleKey ? '✗ fewer than 2 mice: can\'t compare; ⚠ fewer than 3: unstable.' : 'Pooled: no replicates.') + '</small>';
    if(targeted && blocked.length){
      CCCpreviewBlock = "Not enough " + (sampleKey ? "mice" : "cells") + " in " + blocked.join(", ") +
                        " (see the table under Compare conditions)";
    }
    $("#CCCpreview").html(html);
  }).catch(function(err){
    console.error("CCC: could not count replicates:", err);
    $("#CCCpreview").html('<i>Could not count replicates; the server will still check.</i>');
  });
}
$(document).on('change', '#CCCsender, #CCCreceiver, #CCCgroupby, input[name="CCCmode"], input[name="CCCsrcSource"], input[name="CCCdirection"]', function(){
  if($("#CCCcompareBy").val()) CCCupdatePreview();
});

// Disclaimer above the results whenever the comparison view is shown
function CCCshowBanner(meta){
  if(!meta){
    $("#CCCbanner").hide().html("");
    return;
  }
  var notTest = 'These dots are comparable in magnitude but are <b>NOT a statistical test</b>: a visible difference may ' +
                'still be within normal mouse-to-mouse variation. For statistical testing of changes across conditions, ' +
                'a differential analysis across replicates is required (not yet available in this tool).';
  var html = meta.view === 'comparison'
    ? '<b>Comparison view.</b> Unlike the standard dotplot, dots here show ABSOLUTE quantities (percent of cells ' +
      'expressing, and mean expression level), averaged across replicates (mice), NOT LIANA\'s within-run ranks. ' +
      'This is deliberate: ranks are computed separately in each condition and cannot be compared across conditions, ' +
      'so this view replaces them with values that share one scale. ' + notTest
    : '<b>Descriptive view: no replicates.</b> No sample column was chosen, so cells are pooled per condition and ' +
      'mouse-to-mouse variation is unknown; one large mouse can drive a pooled value. Dots show ABSOLUTE quantities ' +
      '(percent of cells expressing, and mean expression level), NOT LIANA\'s within-run ranks, so both conditions ' +
      'share one scale. ' + notTest;
  html += '<br><span style="font-size:12px;">Expression layer: <b>' + CCCesc(meta.layer) + '</b> (' + CCCesc(meta.layer_message) + ').</span>';
  if(meta.layer_status === 'warn'){
    html += ' <span style="font-size:12px; color:#c25e00;"><b>Check this layer before trusting the values.</b></span>';
  }
  $("#CCCbanner").html(html).show();
}

// Validate CCC inputs
function CCCvalidate(){
  var errors = [];

  var groupby = $("#CCCgroupby option:selected").val();
  var mode = $('input[name="CCCmode"]:checked').val();
  if(CCClassoActive()){
    var sel = getCells(null, true);
    if(!sel['celllist1'] || !sel['celllist2']){
      errors.push("Lasso mode needs cells in both Selection 1 and Selection 2");
    }
  } else if(!groupby || groupby === "NA"){
    errors.push("Please select a cell type annotation");
  }

  if(mode === "targeted" && !CCClassoActive()){
    var sender = $("#CCCsender option:selected").val();
    var receiver = $("#CCCreceiver option:selected").val();
    if(!sender) errors.push("Please select a sender cell type");
    if(!receiver) errors.push("Please select a receiver cell type");
  }

  var compareBy = $("#CCCcompareBy option:selected").val();
  if(compareBy){
    var ref = $("#CCCref").val(), test = $("#CCCtest").val();
    if(!ref || !test || ref === test){
      errors.push("Pick two different conditions to compare (reference and test)");
    } else if(CCCpreviewBlock){
      errors.push(CCCpreviewBlock);
    }
  }

  return errors;
}

// Build request object
function CCCbuildRequest(){
  var mode = $('input[name="CCCmode"]:checked').val();
  var cells = $("#CCCcells option:selected").val();
  var groupby = $("#CCCgroupby option:selected").val();
  var compareBy = $("#CCCcompareBy option:selected").val();

  // Get cell indices if specific selection
  var cellIndices = null;
  if(cells !== "all"){
    // Get cells from the store differential state
    var storeState = window.store.getState().differential;
    if(storeState && storeState[cells]){
      cellIndices = Array.from(storeState[cells]);
    } else if(window.accumulateCell && window.accumulateCell[cells]){
      cellIndices = Array.from(window.accumulateCell[cells]);
    }
  }

  var request = {
    method: "CCC",
    mode: mode,
    compute: {
      cells: cells,
      cell_indices: cellIndices,
      groupby: groupby,
      compare_by: compareBy || null,
      compare_levels: compareBy ? [$("#CCCref").val(), $("#CCCtest").val()] : null,
      sample_key: compareBy ? ($("#CCCsample").val() || null) : null,
      layer: $("#CCClayer").val() || "auto",
      min_cells_per_sample: parseInt($("#CCCminCellsSample").val()),
      ccc_method: $("#CCCmethod option:selected").val(),
      resource: $("#CCCresource option:selected").val(),
      min_cells: parseInt($("#CCCminCells").val()) || 20,
      n_perms: parseInt($("#CCCnPerms").val()) || 0,
      max_cells_per_type: parseInt($("#CCCmaxCellsPerType").val()) || 500
    },
    display: {
      sender: mode === "targeted" ? $("#CCCsender option:selected").val() : null,
      receiver: mode === "targeted" ? $("#CCCreceiver option:selected").val() : null,
      direction: $('input[name="CCCdirection"]:checked').val(),
      top_n: parseInt($("#CCCtopN").val()),
      sort_by: $("#CCCsortBy option:selected").val()
    }
  };

  if(CCClassoActive()){
    var sel = getCells(null, true);
    request.compute.cells = "all";
    request.compute.cell_indices = null;
    request.compute.groupby = null;
    request.compute.lasso_groups = {
      "Selection 1": Array.from(sel['celllist1']),
      "Selection 2": Array.from(sel['celllist2'])
    };
    var names = CCClassoNames();
    request.display.sender = names[0];
    request.display.receiver = names[1];
  }

  return request;
}

// Run CCC analysis
function CCCrun(){
  // Validate
  var errors = CCCvalidate();
  if(errors.length > 0){
    $("#CCCnote").html("Error:<br>- " + errors.join("<br>- "));
    return;
  }

  // Clear notes and show spinner
  $("#CCCnote").html("");
  CCCshowBanner(null);
  $("#CCCfig").html("<i>Running LIANA analysis...</i>");
  $("#CCCresultHeader").hide();
  document.getElementById("CCCspin").style.visibility = "visible";
  $(".CCCbt").prop('disabled', true);

  // Build request
  var request = CCCbuildRequest();
  request.figOpt = window.figOpt;
  request.dataset = window.store.getState().config.displayNames.dataset + '.h5ad';

  $.ajax({
    type: "POST",
    url: VIPurl,
    data: JSON.stringify(request),
    contentType: 'application/json;charset=UTF-8',
    success: function(res){
      document.getElementById("CCCspin").style.visibility = "hidden";
      $(".CCCbt").prop("disabled", false);

      if(res.startsWith('ERROR')){
        $('#CCCnote').html(res.replace('ERROR @server: ', '').replace(/\n/g, '<br>'));
        $("#CCCfig").html("<i>Analysis failed. Check error message above.</i>");
        return;
      }

      // Parse response: [csv_data, base64_image]
      var resD;
      try {
        resD = JSON.parse(res);
      } catch(e) {
        // If not JSON, might be an error message as image (from Msg function)
        showImg('CCCfig', res);
        return;
      }

      // Store results for export
      CCClastResults = {
        csv: resD[0],
        data: d3.csvParse(resD[0])
      };

      // Display table
      CCCdisplayTable(resD[0]);

      // Show run details and warnings from the server
      if(resD[2] && resD[2].length > 0){
        $('#CCCnote').html(resD[2].map(function(n){ return $('<div>').text(n).html(); }).join('<br>'));
      }

      // Display image and store for download
      if(resD[1] && resD[1].length > 100){
        CCClastImage = resD[1];
        showImg('CCCfig', resD[1]);
      } else {
        CCClastImage = null;
        $("#CCCfig").html("<i>No visualization available (table above shows results)</i>");
      }

      // Comparison view: disclaimer banner above the results (resD[3] = view/layer metadata)
      CCCshowBanner(resD[3] || null);

      // Show export button and result info
      $("#CCCresultHeader").show();
      var info = CCClastResults.data.length + " rows";
      if(resD[3]){
        info += resD[3].view === "comparison"
          ? " - absolute values, mean across mice; not a statistical test"
          : " - absolute values, cells pooled per condition; descriptive only";
      }
      $("#CCCresultInfo").text(info);

      // Show visualization controls with filter options
      CCCshowVisControls();
    },
    error: function(request, status, error){
      $('#CCCnote').html("Request failed: " + error);
      $("#CCCfig").html("");
      $(".CCCbt").prop("disabled", false);
      document.getElementById("CCCspin").style.visibility = "hidden";
    }
  });
}

// Fill the annotation dropdowns (called each time the CCC tab is opened, so
// new annotations show up; keeps the current choices when still available)
function CCCinit(){
  var grpL = window.store.getState().annoMatrix.schema.annotations.obsByName;
  var prevGroupby = $("#CCCgroupby").val();
  var prevCompareBy = $("#CCCcompareBy").val();

  // Populate groupby dropdown
  $("#CCCgroupby").empty();
  $("#CCCgroupby").append('<option value="NA">-Select-</option>');

  // Populate compareBy dropdown
  $("#CCCcompareBy").empty();
  $("#CCCcompareBy").append('<option value="">None (single condition)</option>');

  for(var key in grpL){
    if(grpL[key].categories && grpL[key].categories.length > 0){
      $("#CCCgroupby").append('<option value="'+key+'">'+key+'</option>');
      $("#CCCcompareBy").append('<option value="'+key+'">'+key+'</option>');
    }
  }
  if(prevGroupby && grpL[prevGroupby]) $("#CCCgroupby").val(prevGroupby);
  if(prevCompareBy && grpL[prevCompareBy]) $("#CCCcompareBy").val(prevCompareBy);
  CCCupdateCompare();
}

// Store last CCC results for export
var CCClastResults = null;

// Display CCC results in a DataTable
function CCCdisplayTable(csvData){
  // Parse CSV data
  var tableD = d3.csvParse(csvData);

  if(tableD.length === 0){
    $('#CCCtableContainer').hide();
    return;
  }

  // Get column names from first row
  var columns = Object.keys(tableD[0]);

  // Build column definitions for DataTables
  var tableTitle = columns.map(function(col){
    // Pretty print column names
    var title = col.replace(/_/g, ' ').replace(/\b\w/g, function(l){ return l.toUpperCase(); });
    return {title: title, data: col};
  });

  // Destroy existing table if present
  if($.fn.DataTable.isDataTable('#CCCtable')){
    $('#CCCtable').DataTable().destroy();
    $('#CCCtable').empty();
  }

  // Show the table container
  $('#CCCtableContainer').show();

  // Initialize DataTable
  $('#CCCtable').DataTable({
    destroy: true,
    dom: 'Blfrtip',
    lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
    order: [],  // keep server order (sorted by the method's score, conditions grouped)
    buttons: ['csv', 'copy'],
    data: tableD,
    columns: tableTitle,
    scrollX: true,
    pageLength: 10
  });
}

// Export CCC results to CSV
function CCCexportCSV(){
  if(!CCClastResults || !CCClastResults.data){
    alert("No results to export. Run analysis first.");
    return;
  }

  // Convert results to CSV format
  var data = CCClastResults.data;
  var headers = Object.keys(data[0]);
  var csv = headers.join(",") + "\n";

  data.forEach(function(row){
    var values = headers.map(function(h){
      var val = row[h];
      // Escape commas and quotes in values
      if(typeof val === "string" && (val.includes(",") || val.includes('"'))){
        val = '"' + val.replace(/"/g, '""') + '"';
      }
      return val;
    });
    csv += values.join(",") + "\n";
  });

  // Download as file
  var blob = new Blob([csv], {type: "text/csv;charset=utf-8;"});
  var link = document.createElement("a");
  var url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", "ccc_results.csv");
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Store the last base64 image for downloading
var CCClastImage = null;

// Show visualization controls and populate filter dropdowns
function CCCshowVisControls(){
  if(!CCClastResults || !CCClastResults.data || CCClastResults.data.length === 0){
    $("#CCCvisControls").hide();
    return;
  }

  // Get unique sources and targets from results
  var sources = new Set();
  var targets = new Set();
  CCClastResults.data.forEach(function(row){
    if(row.source) sources.add(row.source);
    if(row.target) targets.add(row.target);
  });

  // Populate filter dropdowns
  var srcSelect = $("#CCCfilterSource").empty().append('<option value="">All sources</option>');
  var tgtSelect = $("#CCCfilterTarget").empty().append('<option value="">All targets</option>');

  Array.from(sources).sort().forEach(function(s){
    srcSelect.append($('<option>').val(s).text(s));
  });
  Array.from(targets).sort().forEach(function(t){
    tgtSelect.append($('<option>').val(t).text(t));
  });

  $("#CCCvisControls").show();
}

// Update visualization based on current filter settings
function CCCupdateVis(){
  // This will re-request the plot with new parameters
  // For now, just filter the table view
  if(!CCClastResults || !CCClastResults.data) return;

  var source = $("#CCCfilterSource").val();
  var target = $("#CCCfilterTarget").val();
  var topN = parseInt($("#CCCvisTopN").val()) || 20;

  // Filter data
  var filtered = CCClastResults.data.filter(function(row){
    if(source && row.source !== source) return false;
    if(target && row.target !== target) return false;
    return true;
  }).slice(0, topN);

  // Update table with filtered data
  if($.fn.DataTable.isDataTable('#CCCtable')){
    $('#CCCtable').DataTable().clear().rows.add(filtered).draw();
  }

  // Update result info
  $("#CCCresultInfo").text(filtered.length + " of " + CCClastResults.data.length + " interactions shown");
}

// Download the current visualization
function CCCdownloadFig(){
  if(!CCClastImage){
    alert("No visualization to download. Run analysis first.");
    return;
  }

  // Create download link for the base64 image
  var link = document.createElement("a");
  link.href = "data:image/png;base64," + CCClastImage;
  link.download = "ccc_plot.png";
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
