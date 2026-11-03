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

  function makeLeftSidebarCollapsible() {
    var leftSidebar = targetDoc.querySelector('[data-testid="category-sidebar"]') ||
                      targetDoc.querySelector('[class*="leftSidebar"]');

    if (!leftSidebar) {
      var sidebars = targetDoc.querySelectorAll('[class*="sidebar"], [class*="Sidebar"]');
      if (sidebars.length > 0) leftSidebar = sidebars[0];
    }

    if (!leftSidebar || leftSidebar.dataset.vipCollapsible) return;
    leftSidebar.dataset.vipCollapsible = 'true';

    var collapseBtn = targetDoc.createElement('button');
    collapseBtn.id = 'vip-left-collapse-btn';
    collapseBtn.innerHTML = '&#9664;';
    collapseBtn.title = 'Collapse sidebar';
    collapseBtn.style.cssText = 'position: absolute; top: 50%; right: -12px; transform: translateY(-50%); ' +
      'width: 24px; height: 48px; background: #6366F1; color: white; border: none; border-radius: 0 6px 6px 0; ' +
      'cursor: pointer; z-index: 100; font-size: 12px; display: flex; align-items: center; justify-content: center;';

    leftSidebar.style.position = 'relative';
    leftSidebar.appendChild(collapseBtn);

    var isCollapsed = false;

    collapseBtn.onclick = function() {
      isCollapsed = !isCollapsed;
      if (isCollapsed) {
        leftSidebar.style.width = '0px';
        leftSidebar.style.minWidth = '0px';
        leftSidebar.style.overflow = 'hidden';
        leftSidebar.style.padding = '0';
        collapseBtn.innerHTML = '&#9654;';
        collapseBtn.title = 'Expand sidebar';
      } else {
        leftSidebar.style.width = '';
        leftSidebar.style.minWidth = '';
        leftSidebar.style.overflow = '';
        leftSidebar.style.padding = '';
        collapseBtn.innerHTML = '&#9664;';
        collapseBtn.title = 'Collapse sidebar';
      }
    };
  }

  function makeRightSidebarCollapsible() {
    var rightSidebar = targetDoc.querySelector('[data-testid="rightsidebar"]') ||
                       targetDoc.querySelector('[class*="rightSidebar"]');

    if (!rightSidebar) {
      var allDivs = targetDoc.querySelectorAll('div');
      for (var i = 0; i < allDivs.length; i++) {
        var div = allDivs[i];
        var text = div.textContent || '';
        if (text.indexOf('Gene Sets') !== -1 && text.indexOf('Genes') !== -1 && div.offsetWidth < 400) {
          rightSidebar = div;
          break;
        }
      }
    }

    if (!rightSidebar || rightSidebar.dataset.vipCollapsible) return;
    rightSidebar.dataset.vipCollapsible = 'true';

    var collapseBtn = targetDoc.createElement('button');
    collapseBtn.id = 'vip-right-collapse-btn';
    collapseBtn.innerHTML = '&#9654;';
    collapseBtn.title = 'Collapse sidebar';
    collapseBtn.style.cssText = 'position: absolute; top: 50%; left: -12px; transform: translateY(-50%); ' +
      'width: 24px; height: 48px; background: #6366F1; color: white; border: none; border-radius: 6px 0 0 6px; ' +
      'cursor: pointer; z-index: 100; font-size: 12px; display: flex; align-items: center; justify-content: center;';

    rightSidebar.style.position = 'relative';
    rightSidebar.appendChild(collapseBtn);

    var isCollapsed = false;

    collapseBtn.onclick = function() {
      isCollapsed = !isCollapsed;
      if (isCollapsed) {
        rightSidebar.style.width = '0px';
        rightSidebar.style.minWidth = '0px';
        rightSidebar.style.overflow = 'hidden';
        rightSidebar.style.padding = '0';
        collapseBtn.innerHTML = '&#9664;';
        collapseBtn.title = 'Expand sidebar';
      } else {
        rightSidebar.style.width = '';
        rightSidebar.style.minWidth = '';
        rightSidebar.style.overflow = '';
        rightSidebar.style.padding = '';
        collapseBtn.innerHTML = '&#9654;';
        collapseBtn.title = 'Collapse sidebar';
      }
    };
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
