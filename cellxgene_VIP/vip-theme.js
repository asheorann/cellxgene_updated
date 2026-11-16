/**
 * VIP Theme JavaScript
 * UI helpers for the modern VIP theme.
 * Runs in parent document context (main cellxgene).
 */

(function() {
  'use strict';

  // Get the target document (parent if we're in VIP panel, otherwise current)
  var targetDoc = (window.parent && window.parent.document && window.parent !== window)
    ? window.parent.document
    : document;

  // ============================================
  // FIX JSPANEL HEADER (remove gray background)
  // ============================================

  function fixJsPanelHeader() {
    var headerbar = targetDoc.querySelector('.jsPanel-headerbar');
    if (headerbar) {
      headerbar.style.background = 'white';
      headerbar.style.overflow = 'visible';
    }
    var titlebar = targetDoc.querySelector('.jsPanel-titlebar');
    if (titlebar) {
      titlebar.style.overflow = 'visible';
      titlebar.style.minWidth = '250px';
    }
    var title = targetDoc.querySelector('.jsPanel-title');
    if (title) {
      title.style.overflow = 'visible';
      title.style.whiteSpace = 'nowrap';
    }
  }

  // Run periodically to catch when jsPanel is created
  setInterval(fixJsPanelHeader, 500);

  // ============================================
  // COLLAPSED GENE SETS EXPAND BUTTON
  // ============================================
  // DISABLED: This feature was causing issues (button showing when it shouldn't)
  // The right sidebar in cellxgene already has built-in collapse/expand

  // Clean up any leftover buttons from previous code
  function cleanupOldButtons() {
    var oldButtons = [
      'vip-gene-expand-btn',
      'vip-left-collapse-btn',
      'vip-right-collapse-btn'
    ];
    oldButtons.forEach(function(id) {
      var btn = targetDoc.getElementById(id);
      if (btn) btn.remove();
    });
  }
  // Run cleanup once after page loads
  setTimeout(cleanupOldButtons, 1000);

  // ============================================
  // TOOL SELECTION HIGHLIGHTING
  // ============================================

  function highlightSelectedTools() {
    // Find all tool buttons in the menubar
    var toolButtons = targetDoc.querySelectorAll(
      '.bp5-button-group .bp5-button, .bp4-button-group .bp4-button, ' +
      '[data-testid*="lasso"], [data-testid*="select"], [data-testid*="brush"], ' +
      '[aria-label*="lasso"], [aria-label*="select"], [aria-label*="brush"]'
    );

    toolButtons.forEach(function(btn) {
      // Check if button is active/pressed
      var isActive = btn.classList.contains('bp5-active') ||
                     btn.classList.contains('bp4-active') ||
                     btn.getAttribute('aria-pressed') === 'true' ||
                     btn.getAttribute('aria-selected') === 'true';

      if (isActive) {
        btn.style.background = '#6366F1';
        btn.style.color = 'white';
        btn.style.boxShadow = '0 0 0 2px #EEF2FF';
        // Also color the icon
        var icon = btn.querySelector('svg, .bp5-icon, .bp4-icon');
        if (icon) {
          icon.style.color = 'white';
          icon.style.fill = 'white';
        }
      }
    });
  }

  // Run periodically to catch tool selection changes
  setInterval(highlightSelectedTools, 300);

  // ============================================
  // ORGANIZE VIP TABS INTO CATEGORIES
  // ============================================

  function organizeVIPTabs() {
    // Find the VIP panel content (inside jsPanel)
    var vipPanel = targetDoc.querySelector('.jsPanel-content');
    if (!vipPanel) {
      // Try within current document (if we're inside VIP)
      vipPanel = document.querySelector('.tab');
    }

    var tabContainer = vipPanel ? vipPanel.querySelector('.tab') : document.querySelector('.tab');
    if (!tabContainer || tabContainer.dataset.vipOrganized) return;

    tabContainer.dataset.vipOrganized = 'true';

    // Get all tab buttons
    var buttons = tabContainer.querySelectorAll('.tablinks');
    if (buttons.length === 0) return;

    // Define categories
    var categories = {
      'Gene Input': ['Add Genes'],
      'Expression Plots': ['Violin', 'Heatmap', 'Dot Plot', 'Track Plot', 'Embedding Plot'],
      'Distribution': ['Density Plot', 'Density Scatter', 'Dual Genes'],
      'Composition': ['Sankey Diagram', 'Stacked Barplot'],
      'Analysis': ['Gene Specificity', 'Gene Detected', 'DEG', 'Pre-Computed DEG', 'Marker Genes', 'CCC:'],
      'Spatial': ['Spatial Transcriptomics', 'Multiome', 'CosMx', 'Visium'],
      'Utilities': ['Command Line Interface', 'Brush', 'Sync'],
      'Settings': ['Global Setting', 'Comb. & Abbr.', 'Save Session', 'Load Session', 'Check All Annotations']
    };

    // Create new organized structure
    var newContainer = document.createElement('div');
    newContainer.className = 'vip-categories';

    Object.keys(categories).forEach(function(catName) {
      var catButtons = [];

      categories[catName].forEach(function(btnText) {
        buttons.forEach(function(btn) {
          var text = btn.textContent.trim();
          if (text === btnText || text.indexOf(btnText) !== -1) {
            catButtons.push(btn.cloneNode(true));
          }
        });
      });

      if (catButtons.length === 0) return;

      // Create category section
      var section = document.createElement('div');
      section.className = 'vip-category';

      var header = document.createElement('div');
      header.className = 'vip-category-header';
      header.innerHTML = '<span class="vip-category-title">' + catName + '</span><span class="vip-category-arrow">&#9660;</span>';

      var content = document.createElement('div');
      content.className = 'vip-category-content';

      catButtons.forEach(function(btn) {
        content.appendChild(btn);
      });

      section.appendChild(header);
      section.appendChild(content);
      newContainer.appendChild(section);

      // Toggle collapse
      header.onclick = function() {
        section.classList.toggle('collapsed');
      };
    });

    // Replace old container content
    tabContainer.innerHTML = '';
    tabContainer.appendChild(newContainer);
  }

  // ============================================
  // RENAME "VISUALIZATION IN PLUGIN" TO "ANALYZE"
  // ============================================

  function renameVIPButton() {
    var buttons = targetDoc.querySelectorAll('button, .bp5-button, .bp4-button, .bp3-button');
    buttons.forEach(function(btn) {
      if (btn.textContent && btn.textContent.indexOf('VISUALIZATION') !== -1) {
        var walker = document.createTreeWalker(btn, NodeFilter.SHOW_TEXT, null, false);
        var node;
        while (node = walker.nextNode()) {
          if (node.textContent.indexOf('VISUALIZATION') !== -1) {
            node.textContent = 'ANALYZE';
          }
        }
        btn.querySelectorAll('span').forEach(function(span) {
          if (span.textContent.indexOf('VISUALIZATION') !== -1) {
            span.textContent = 'ANALYZE';
          }
        });
        btn.dataset.vipRenamed = 'true';
      }
    });
    setTimeout(renameVIPButton, 2000);
  }

  // ============================================
  // COLLAPSIBLE SIDEBARS
  // ============================================
  // DISABLED: These custom collapse buttons were causing issues
  // (VIP panel disappearing, unexpected behavior)
  // CellxGene already has built-in collapse for gene panel

  function makeLeftSidebarCollapsible() {
    // Disabled - was causing issues
  }

  function makeRightSidebarCollapsible() {
    // Disabled - was causing issues
  }

  // ============================================
  // TUTORIAL SYSTEM WITH PRECISE HIGHLIGHTING
  // ============================================

  var VIPTutorial = {
    currentStep: 0,
    steps: [
      {
        title: "Welcome to CellxGene VIP",
        content: "This quick tour will help you get started with the visualization tools. Click 'Next' to continue.",
        targets: null,
        position: "center"
      },
      {
        title: "Step 1: Filter by Categories",
        content: "Use these checkboxes to filter cells by metadata like cell type, tissue, or donor. Click on a category name to expand it.",
        targets: [
          '[data-testid="category-sidebar"]',
          '[class*="leftSidebar"]',
          '[class*="category"]'
        ],
        position: "right"
      },
      {
        title: "Step 2: Select Cells with Lasso",
        content: "Click this lasso tool, then draw around cells in the scatter plot to select them. Selected cells will be used in your visualizations.",
        targets: [
          '[data-testid="lasso-select"]',
          'button[title*="lasso"]',
          'button[title*="Lasso"]',
          '[class*="lasso"]',
          '.bp5-button-group button:nth-child(2)',
          '.bp4-button-group button:nth-child(2)'
        ],
        position: "bottom"
      },
      {
        title: "Step 3: Open Analysis Panel",
        content: "Click here to open the VIP panel with advanced visualizations like heatmaps, violin plots, and dot plots.",
        targets: [
          'button[data-vip-renamed]',
          '[class*="visualization"]',
          '.bp5-popover-target button'
        ],
        position: "bottom"
      },
      {
        title: "Step 4: Explore Genes",
        content: "Search for genes here and add them to your gene list. These genes will be used in your visualizations.",
        targets: [
          '[data-testid="rightsidebar"]',
          '[class*="rightSidebar"]',
          '[class*="gene-search"]'
        ],
        position: "left"
      },
      {
        title: "Step 5: View Cell Count",
        content: "This shows how many cells are currently selected. Selection 1 and Selection 2 can be used for comparisons.",
        targets: [
          '[class*="cell-count"]',
          '[class*="selection"]',
          'span:contains("cells")'
        ],
        position: "bottom"
      }
    ],

    init: function() {
      if (targetDoc.getElementById('vip-tutorial-overlay')) return;
      this.createOverlay();
      this.createHelpButton();
    },

    createOverlay: function() {
      var overlay = targetDoc.createElement('div');
      overlay.id = 'vip-tutorial-overlay';
      overlay.innerHTML =
        '<div class="vip-tutorial-backdrop"></div>' +
        '<div class="vip-tutorial-spotlight"></div>' +
        '<div class="vip-tutorial-modal">' +
          '<div class="vip-tutorial-header">' +
            '<span class="vip-tutorial-step-indicator"></span>' +
            '<button class="vip-tutorial-close">&times;</button>' +
          '</div>' +
          '<h3 class="vip-tutorial-title"></h3>' +
          '<p class="vip-tutorial-content"></p>' +
          '<div class="vip-tutorial-footer">' +
            '<button class="vip-tutorial-btn vip-tutorial-btn-skip">Skip Tour</button>' +
            '<div class="vip-tutorial-nav">' +
              '<button class="vip-tutorial-btn vip-tutorial-btn-prev">Back</button>' +
              '<button class="vip-tutorial-btn vip-tutorial-btn-next">Next</button>' +
            '</div>' +
          '</div>' +
        '</div>';

      targetDoc.body.appendChild(overlay);

      var self = this;
      overlay.querySelector('.vip-tutorial-close').onclick = function() { self.close(); };
      overlay.querySelector('.vip-tutorial-btn-skip').onclick = function() { self.close(); };
      overlay.querySelector('.vip-tutorial-btn-prev').onclick = function() { self.prev(); };
      overlay.querySelector('.vip-tutorial-btn-next').onclick = function() { self.next(); };
    },

    createHelpButton: function() {
      var btn = targetDoc.createElement('button');
      btn.id = 'vip-help-btn';
      btn.innerHTML = '?';
      btn.title = 'Quick Tutorial';

      var self = this;
      btn.onclick = function() { self.start(); };

      targetDoc.body.appendChild(btn);
    },

    start: function() {
      this.currentStep = 0;
      this.showStep();
      targetDoc.getElementById('vip-tutorial-overlay').classList.add('active');
    },

    close: function() {
      targetDoc.getElementById('vip-tutorial-overlay').classList.remove('active');
      this.clearSpotlight();
    },

    next: function() {
      if (this.currentStep < this.steps.length - 1) {
        this.currentStep++;
        this.showStep();
      } else {
        this.close();
      }
    },

    prev: function() {
      if (this.currentStep > 0) {
        this.currentStep--;
        this.showStep();
      }
    },

    findTarget: function(selectors) {
      if (!selectors) return null;
      for (var i = 0; i < selectors.length; i++) {
        var target = targetDoc.querySelector(selectors[i]);
        if (target && target.offsetWidth > 0) {
          return target;
        }
      }
      return null;
    },

    showStep: function() {
      var step = this.steps[this.currentStep];
      var overlay = targetDoc.getElementById('vip-tutorial-overlay');
      var modal = overlay.querySelector('.vip-tutorial-modal');
      var spotlight = overlay.querySelector('.vip-tutorial-spotlight');

      // Update content
      overlay.querySelector('.vip-tutorial-step-indicator').textContent =
        'Step ' + (this.currentStep + 1) + ' of ' + this.steps.length;
      overlay.querySelector('.vip-tutorial-title').textContent = step.title;
      overlay.querySelector('.vip-tutorial-content').textContent = step.content;

      // Update buttons
      var prevBtn = overlay.querySelector('.vip-tutorial-btn-prev');
      var nextBtn = overlay.querySelector('.vip-tutorial-btn-next');
      prevBtn.style.display = this.currentStep === 0 ? 'none' : 'inline-flex';
      nextBtn.textContent = this.currentStep === this.steps.length - 1 ? 'Finish' : 'Next';

      // Find and spotlight target
      this.clearSpotlight();

      var target = this.findTarget(step.targets);

      if (target) {
        var rect = target.getBoundingClientRect();
        var padding = 8;

        // Position spotlight with padding
        spotlight.style.display = 'block';
        spotlight.style.top = (rect.top - padding) + 'px';
        spotlight.style.left = (rect.left - padding) + 'px';
        spotlight.style.width = (rect.width + padding * 2) + 'px';
        spotlight.style.height = (rect.height + padding * 2) + 'px';
        spotlight.style.borderRadius = '8px';

        // Position modal next to spotlight
        var modalWidth = 380;
        var windowWidth = window.innerWidth;
        var windowHeight = window.innerHeight;

        modal.style.position = 'fixed';
        modal.style.maxWidth = modalWidth + 'px';

        if (step.position === 'right' && rect.right + modalWidth + 40 < windowWidth) {
          modal.style.top = Math.max(20, Math.min(rect.top, windowHeight - 300)) + 'px';
          modal.style.left = (rect.right + 20) + 'px';
          modal.style.transform = 'none';
        } else if (step.position === 'left' && rect.left - modalWidth - 40 > 0) {
          modal.style.top = Math.max(20, Math.min(rect.top, windowHeight - 300)) + 'px';
          modal.style.left = (rect.left - modalWidth - 20) + 'px';
          modal.style.transform = 'none';
        } else if (step.position === 'bottom' && rect.bottom + 200 < windowHeight) {
          modal.style.top = (rect.bottom + 20) + 'px';
          modal.style.left = Math.max(20, Math.min(rect.left, windowWidth - modalWidth - 20)) + 'px';
          modal.style.transform = 'none';
        } else {
          // Default: position to the right or center
          modal.style.top = Math.max(20, rect.top) + 'px';
          modal.style.left = Math.min(rect.right + 20, windowWidth - modalWidth - 20) + 'px';
          modal.style.transform = 'none';
        }

        return;
      }

      // No target found - center modal
      spotlight.style.display = 'none';
      this.centerModal(modal);
    },

    centerModal: function(modal) {
      modal.style.position = 'fixed';
      modal.style.top = '50%';
      modal.style.left = '50%';
      modal.style.transform = 'translate(-50%, -50%)';
      modal.style.maxWidth = '420px';
    },

    clearSpotlight: function() {
      var spotlight = targetDoc.querySelector('.vip-tutorial-spotlight');
      if (spotlight) {
        spotlight.style.display = 'none';
      }
    }
  };

  // Make globally accessible
  if (window.parent && window.parent !== window) {
    window.parent.VIPTutorial = VIPTutorial;
  }
  window.VIPTutorial = VIPTutorial;

  // ============================================
  // INFO TOOLTIPS FOR VIP SETTINGS
  // ============================================

  // Define all settings that need info tooltips
  // Key: text to match (label content), Value: tooltip explanation
  var VIP_SETTING_TOOLTIPS = {
    // === Violin Plot Settings ===
    'Choose cell selection': 'Select which cell populations to include. Use lasso tool on the main plot to define selections.',
    'Choose a gene': 'Select a gene to visualize. Add genes first using the "Add Genes" tab.',
    'Expression cutoff for cell filtering': 'Cells with expression below this value are excluded from the plot.',
    'Dot size for cells': 'Controls the size of individual data points in the violin plot.',
    'Group by': 'Categorical annotation to split the data by (e.g., cell type, cluster).',
    'Sub-group by': 'Secondary grouping within each main group for comparison.',

    // === Heatmap Settings ===
    'Choose genes': 'Select genes to display in the heatmap. Add genes first using "Add Genes".',
    'Choose categorical annotation': 'Metadata columns (like cell type) to display as color bars.',
    'Choose continuous annotation': 'Numeric metadata to display as a continuous color gradient.',
    'Select plotting value': 'Expression: raw values. Z-score: normalized to mean=0, sd=1 per gene.',
    'Color': 'Color palette for the heatmap. Sequential for expression, diverging for z-scores.',
    'Reverse': 'Flip the color scale direction.',
    'Select plotting methods': 'ComplexHeatmap (R): More customization. Seaborn: Faster, simpler.',
    'Gene as': 'Whether genes appear as rows or columns in the heatmap.',
    'Width': 'Figure width in inches.',
    'Height': 'Figure height in inches.',
    'Annotation fontsize adjust': 'Fine-tune annotation text size (-10 to +10).',
    'Cluster by': 'Annotation: order by metadata. Expression: hierarchical clustering.',
    'Max legend row': 'Limit legend rows when genes are displayed as rows.',

    // === Dot Plot Settings ===
    'Expression cutoff for cell fraction': 'Minimum expression for a cell to count as "expressing" (affects dot size).',
    'Expression is averaged only over cells expressing': 'Yes: mean of expressing cells only. No: mean of all cells.',
    'Adjust the legend width': 'Control the width of the legend area.',

    // === Gene Sets Settings ===
    'Collapsing the above gene sets': 'Combine gene set scores into a single value per cell.',
    'By': 'Average: mean expression. Median: middle value (robust to outliers).',

    // === Embedding Plot Settings ===
    'Choose an embedding': 'Dimensionality reduction to visualize (UMAP, t-SNE, PCA, etc.).',
    'Color by': 'What to color points by: gene expression or metadata.',

    // === Density Plot Settings ===
    'Kernel bandwidth': 'Smoothing factor. Higher = smoother curves.',

    // === Track Plot Settings ===
    'Track height': 'Height of each gene track in the plot.',

    // === Sankey Diagram Settings ===
    'Source annotation': 'Left side of the flow diagram.',
    'Target annotation': 'Right side of the flow diagram.',

    // === DEG Settings ===
    'Test method': 'Statistical test for differential expression. Wilcoxon: non-parametric. t-test: parametric.',
    'Correction method': 'Multiple testing correction. Benjamini-Hochberg controls false discovery rate.',
    'Log2 fold change cutoff': 'Minimum expression difference to consider significant.',
    'Adjusted p-value cutoff': 'Maximum adjusted p-value for significance.',

    // === Spatial Settings ===
    'Spot size': 'Size of spatial spots in the visualization.',
    'Alpha': 'Transparency of spots (0=invisible, 1=opaque).',

    // === Global Settings ===
    'Figure DPI': 'Image resolution. Higher = larger file, sharper image.',
    'Font size': 'Base text size for all plot labels.',
    'Figure format': 'Output format: PNG (raster), SVG (vector), PDF (print).',

    // === Add Genes Settings ===
    'Case sensitive': 'Whether gene name matching is case-sensitive.',
    'Regex': 'Enable regular expression pattern matching for gene names.',
    'Exact match': 'Only match complete gene names, not partial matches.'
  };

  function injectInfoTooltips() {
    // Get the VIP panel content
    var vipPanel = targetDoc.querySelector('.jsPanel-content');
    if (!vipPanel) return;

    // Also check current document if we're inside VIP
    var doc = vipPanel || document;

    // Find all paragraphs and labels that might contain settings
    var elements = doc.querySelectorAll('p, label, span');

    elements.forEach(function(el) {
      // Skip if already has tooltip
      if (el.querySelector('.vip-info')) return;
      if (el.classList.contains('vip-info')) return;

      var text = el.textContent || '';

      // Check each tooltip definition
      Object.keys(VIP_SETTING_TOOLTIPS).forEach(function(key) {
        // Match if the element text starts with or contains the key
        if (text.indexOf(key) !== -1 && text.indexOf(key) < 50) {
          // Don't add to elements that are mostly input/select
          var inputs = el.querySelectorAll('input, select');
          var isInputContainer = inputs.length > 0 && el.textContent.trim().length < key.length + 20;

          // Find the text node or create a place for the tooltip
          var firstChild = el.firstChild;
          if (firstChild && firstChild.nodeType === Node.TEXT_NODE) {
            // Insert after the label text but before inputs
            var info = targetDoc.createElement('span');
            info.className = 'vip-info';
            info.textContent = 'i';
            info.title = VIP_SETTING_TOOLTIPS[key];
            info.style.cssText = 'display:inline-flex;align-items:center;justify-content:center;' +
              'width:14px;height:14px;border-radius:50%;background:#6366F1;color:white;' +
              'font-size:10px;font-weight:bold;cursor:help;margin-left:4px;font-style:normal;' +
              'vertical-align:middle;';

            // Insert after the text content
            if (el.querySelector('select, input')) {
              // Insert before the first input/select
              var firstInput = el.querySelector('select, input');
              el.insertBefore(info, firstInput);
            } else {
              // Append at end
              el.appendChild(info);
            }
          }
        }
      });
    });
  }

  // Run periodically to catch dynamically loaded content
  setInterval(injectInfoTooltips, 2000);

  // ============================================
  // INITIALIZE
  // ============================================

  function init() {
    console.log('[VIP Theme] Initializing...');

    renameVIPButton();
    setTimeout(makeLeftSidebarCollapsible, 1000);
    setTimeout(makeRightSidebarCollapsible, 1000);
    VIPTutorial.init();

    // DISABLED: Category reorganization was causing issues (non-clickable buttons)
    // TODO: Fix this later - need to preserve onclick handlers when moving buttons
    // setInterval(function() {
    //   var vipContent = targetDoc.querySelector('.jsPanel-content .tab');
    //   if (vipContent && !vipContent.dataset.vipOrganized) {
    //     organizeVIPTabs();
    //   }
    // }, 1000);

    console.log('[VIP Theme] Initialized');
  }

  if (targetDoc.readyState === 'loading') {
    targetDoc.addEventListener('DOMContentLoaded', function() {
      setTimeout(init, 500);
    });
  } else {
    setTimeout(init, 500);
  }

})();
