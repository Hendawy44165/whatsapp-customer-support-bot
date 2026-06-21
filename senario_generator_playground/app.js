// State Management
let currentScenarios = [];
let auditStates = {};
let editingId = null;

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
  loadData();
  renderScenarios();
  updateStats();
  setupEventListeners();
  
  // Initialize Lucide Icons
  lucide.createIcons();
});

// Load Data from LocalStorage or default scenarios
function loadData() {
  const savedScenarios = localStorage.getItem("playground_scenarios");
  const savedAuditStates = localStorage.getItem("playground_audit_states");

  if (savedScenarios) {
    currentScenarios = JSON.parse(savedScenarios);
  } else {
    // Clone the scenarios array from scenarios.js to avoid reference mutation
    currentScenarios = JSON.parse(JSON.stringify(scenarios));
    localStorage.setItem("playground_scenarios", JSON.stringify(currentScenarios));
  }

  if (savedAuditStates) {
    auditStates = JSON.parse(savedAuditStates);
  } else {
    // Default all to unreviewed
    currentScenarios.forEach(s => {
      auditStates[s.id] = "unreviewed";
    });
    localStorage.setItem("playground_audit_states", JSON.stringify(auditStates));
  }
}

// Save current state to localStorage
function saveState() {
  localStorage.setItem("playground_scenarios", JSON.stringify(currentScenarios));
  localStorage.setItem("playground_audit_states", JSON.stringify(auditStates));
  updateStats();
}

// Update stats count in sidebar
function updateStats() {
  const total = currentScenarios.length;
  document.getElementById("stat-total").textContent = total;

  const approvedCount = Object.values(auditStates).filter(state => state === "approved").length;
  document.getElementById("stat-audited").textContent = `${approvedCount} / ${total}`;

  // Current filtered count is updated during render
}

// Get Badge Classes
function getTopicClass(topic) {
  if (topic === "Return") return "topic-return";
  if (topic === "Exchange") return "topic-exchange";
  if (topic === "WISMO") return "topic-wismo";
  if (topic === "General Info") return "topic-info";
  return "topic-unrelated";
}

function getEmotionClass(emotion) {
  if (emotion === "Very Positive") return "em-vpos";
  if (emotion === "Positive") return "em-pos";
  if (emotion === "Neutral") return "em-neutral";
  if (emotion === "Negative") return "em-neg";
  return "em-vneg";
}

function getPriorityClass(priority) {
  if (priority.includes("Very urgent") || priority.includes("Urgent")) return "pr-high";
  if (priority.includes("Important")) return "pr-med";
  return "pr-low";
}

function getAvatarClass(persona) {
  if (persona.includes("Susan")) return "avatar-susan";
  if (persona.includes("Chaz")) return "avatar-chaz";
  if (persona.includes("Yasmin")) return "avatar-yasmin";
  if (persona.includes("Arthur")) return "avatar-arthur";
  if (persona.includes("Chloe")) return "avatar-chloe";
  if (persona.includes("Mustafa")) return "avatar-mustafa";
  return "avatar-unknown";
}

function getAvatarInitials(persona) {
  if (persona.includes("Susan")) return "SU";
  if (persona.includes("Chaz")) return "CH";
  if (persona.includes("Yasmin")) return "YA";
  if (persona.includes("Arthur")) return "AR";
  if (persona.includes("Chloe")) return "CL";
  if (persona.includes("Mustafa")) return "MU";
  return "US";
}

// Render Scenario Cards
function renderScenarios() {
  const container = document.getElementById("scenarios-container");
  container.innerHTML = "";

  const filtered = filterScenarios();
  
  document.getElementById("stat-matching").textContent = filtered.length;
  document.getElementById("results-count").textContent = filtered.length;

  if (filtered.length === 0) {
    document.getElementById("empty-state").classList.remove("hidden");
    container.classList.add("hidden");
    return;
  } else {
    document.getElementById("empty-state").classList.add("hidden");
    container.classList.remove("hidden");
  }

  filtered.forEach(scenario => {
    const state = auditStates[scenario.id] || "unreviewed";
    const isEditing = editingId === scenario.id;

    const card = document.createElement("div");
    card.className = `scenario-card ${state}`;
    card.id = `card-${scenario.id}`;

    // Header structure
    let headerHTML = `
      <div class="card-header-row">
        <span class="scenario-id">ID: #${scenario.id}</span>
        <div class="audit-selector">
          <span class="audit-badge audit-badge-unreviewed ${state === 'unreviewed' ? 'active' : ''}" onclick="setAuditState(${scenario.id}, 'unreviewed')" title="Mark as Unreviewed">
            <i data-lucide="help-circle" style="width:12px;height:12px"></i>
          </span>
          <span class="audit-badge audit-badge-approved ${state === 'approved' ? 'active' : ''}" onclick="setAuditState(${scenario.id}, 'approved')" title="Mark as Approved">
            <i data-lucide="check" style="width:12px;height:12px"></i>
          </span>
          <span class="audit-badge audit-badge-flagged ${state === 'flagged' ? 'active' : ''}" onclick="setAuditState(${scenario.id}, 'flagged')" title="Mark as Flagged">
            <i data-lucide="flag" style="width:12px;height:12px"></i>
          </span>
        </div>
      </div>
    `;

    // Persona Section
    let personaHTML = `
      <div class="persona-info">
        <div class="persona-avatar ${getAvatarClass(scenario.persona)}">
          ${getAvatarInitials(scenario.persona)}
        </div>
        <div class="persona-details">
          <span class="persona-name">${scenario.persona.split(" (")[0]}</span>
          <span class="persona-role">${scenario.persona.split(" (")[1]?.replace(")", "") || ""}</span>
        </div>
      </div>
    `;

    // Metadata Badges Section
    let badgesHTML = `
      <div class="meta-badges">
        <span class="badge badge-topic ${getTopicClass(scenario.topic)}">
          <i data-lucide="tag" style="width:11px;height:11px"></i> ${scenario.topic}
        </span>
        <span class="badge badge-emotion ${getEmotionClass(scenario.emotion)}">
          <i data-lucide="smile" style="width:11px;height:11px"></i> ${scenario.emotion}
        </span>
        <span class="badge badge-priority ${getPriorityClass(scenario.priority)}">
          <i data-lucide="clock" style="width:11px;height:11px"></i> ${scenario.priority.split(" but ")[0]}
        </span>
      </div>
    `;

    // Chat Input bubble and editor
    let chatHTML = `
      <div class="chat-container">
        <div class="chat-label">
          <span>Customer Message</span>
          <span class="edit-pill" style="font-size:0.65rem; color:var(--text-muted)">
            ${isEditing ? 'Editing...' : ''}
          </span>
        </div>
        ${
          isEditing 
            ? `<textarea id="textarea-${scenario.id}" class="chat-textarea">${scenario.user_input}</textarea>`
            : `<p class="chat-bubble" id="bubble-${scenario.id}">${escapeHtml(scenario.user_input)}</p>`
        }
      </div>
    `;

    // Actions Footer
    let actionsHTML = `
      <div class="card-actions">
        <div class="edit-actions">
          ${
            isEditing
              ? `
                <button class="icon-btn icon-btn-success" onclick="saveEdit(${scenario.id})" title="Save Edits">
                  <i data-lucide="check"></i>
                </button>
                <button class="icon-btn icon-btn-danger" onclick="cancelEdit()" title="Cancel Edits">
                  <i data-lucide="x"></i>
                </button>
                `
              : `
                <button class="icon-btn icon-btn-primary" onclick="startEdit(${scenario.id})" title="Edit Scenario Input">
                  <i data-lucide="edit-3"></i>
                </button>
                `
          }
        </div>
        <button class="icon-btn" onclick="copyToClipboard(${scenario.id}, '${escapeQuote(scenario.user_input)}')" title="Copy to Clipboard">
          <i data-lucide="copy" id="copy-icon-${scenario.id}"></i>
        </button>
      </div>
    `;

    card.innerHTML = headerHTML + personaHTML + badgesHTML + chatHTML + actionsHTML;
    container.appendChild(card);
  });

  // Re-run lucide icons render
  lucide.createIcons();
}

// Helper to escape HTML characters
function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Helper to escape quotes for inline JS arguments
function escapeQuote(text) {
  return text.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// Filter datasets based on dropdown values
function filterScenarios() {
  const searchQuery = document.getElementById("search-input").value.toLowerCase();
  const topicFilter = document.getElementById("filter-topic").value;
  const emotionFilter = document.getElementById("filter-emotion").value;
  const priorityFilter = document.getElementById("filter-priority").value;
  const personaFilter = document.getElementById("filter-persona").value;
  const auditFilter = document.getElementById("filter-audit").value;

  return currentScenarios.filter(scenario => {
    // Text search filter (matches text in user_input, persona, or metadata)
    const matchesSearch = 
      scenario.user_input.toLowerCase().includes(searchQuery) ||
      scenario.persona.toLowerCase().includes(searchQuery) ||
      scenario.topic.toLowerCase().includes(searchQuery);

    // Dropdown filters
    const matchesTopic = topicFilter === "all" || scenario.topic === topicFilter;
    const matchesEmotion = emotionFilter === "all" || scenario.emotion === emotionFilter;
    const matchesPriority = priorityFilter === "all" || scenario.priority === priorityFilter;
    const matchesPersona = personaFilter === "all" || scenario.persona.includes(personaFilter);
    
    const currentAuditState = auditStates[scenario.id] || "unreviewed";
    const matchesAudit = auditFilter === "all" || currentAuditState === auditFilter;

    return matchesSearch && matchesTopic && matchesEmotion && matchesPriority && matchesPersona && matchesAudit;
  });
}

// Event Listeners Setup
function setupEventListeners() {
  // Dropdown filter changes
  document.getElementById("search-input").addEventListener("input", () => {
    renderScenarios();
  });
  document.getElementById("filter-topic").addEventListener("change", renderScenarios);
  document.getElementById("filter-emotion").addEventListener("change", renderScenarios);
  document.getElementById("filter-priority").addEventListener("change", renderScenarios);
  document.getElementById("filter-persona").addEventListener("change", renderScenarios);
  document.getElementById("filter-audit").addEventListener("change", renderScenarios);

  // Clear Filters button
  document.getElementById("clear-filters-btn").addEventListener("click", resetFilters);
  document.getElementById("empty-reset-btn").addEventListener("click", resetFilters);

  // Reset Audit States button
  document.getElementById("reset-audit-btn").addEventListener("click", () => {
    if (confirm("Are you sure you want to reset all audit statuses to 'Unreviewed'? This won't delete your scenario text edits.")) {
      currentScenarios.forEach(s => {
        auditStates[s.id] = "unreviewed";
      });
      saveState();
      renderScenarios();
      showToast("Audit states successfully reset!", "info");
    }
  });

  // Export JSON button
  document.getElementById("export-json-btn").addEventListener("click", exportDataset);

  // Grid / List View Toggle
  document.getElementById("view-grid").addEventListener("click", (e) => {
    document.getElementById("view-grid").classList.add("active");
    document.getElementById("view-list").classList.remove("active");
    document.getElementById("scenarios-container").classList.remove("list-view");
  });

  document.getElementById("view-list").addEventListener("click", (e) => {
    document.getElementById("view-list").classList.add("active");
    document.getElementById("view-grid").classList.remove("active");
    document.getElementById("scenarios-container").classList.add("list-view");
  });
}

// Reset Filters values
function resetFilters() {
  document.getElementById("search-input").value = "";
  document.getElementById("filter-topic").value = "all";
  document.getElementById("filter-emotion").value = "all";
  document.getElementById("filter-priority").value = "all";
  document.getElementById("filter-persona").value = "all";
  document.getElementById("filter-audit").value = "all";
  renderScenarios();
  showToast("Filters cleared", "info");
}

// Audit state change handler
window.setAuditState = function(id, state) {
  auditStates[id] = state;
  saveState();
  
  // Instantly update card styling classes without full re-render for performance
  const card = document.getElementById(`card-${id}`);
  if (card) {
    card.className = `scenario-card ${state}`;
    
    // Update active state on badges
    const badges = card.querySelectorAll(".audit-badge");
    badges.forEach(badge => {
      badge.classList.remove("active");
      if (badge.classList.contains(`audit-badge-${state}`)) {
        badge.classList.add("active");
      }
    });
  }

  showToast(`Scenario #${id} marked as ${state.toUpperCase()}`, "success");
};

// Inline Editor start
window.startEdit = function(id) {
  editingId = id;
  renderScenarios();
  
  // Set focus on the created textarea
  const textarea = document.getElementById(`textarea-${id}`);
  if (textarea) {
    textarea.focus();
    // Position cursor at the end of the text
    const val = textarea.value;
    textarea.value = "";
    textarea.value = val;
  }
};

// Save edited input
window.saveEdit = function(id) {
  const textarea = document.getElementById(`textarea-${id}`);
  if (textarea) {
    const newText = textarea.value.trim();
    if (newText === "") {
      alert("Scenario input cannot be completely empty.");
      return;
    }
    
    const scenarioIndex = currentScenarios.findIndex(s => s.id === id);
    if (scenarioIndex !== -1) {
      currentScenarios[scenarioIndex].user_input = newText;
      saveState();
      editingId = null;
      renderScenarios();
      showToast(`Scenario #${id} edited successfully!`, "success");
    }
  }
};

// Cancel editing
window.cancelEdit = function() {
  editingId = null;
  renderScenarios();
};

// Copy user message to clipboard
window.copyToClipboard = function(id, text) {
  navigator.clipboard.writeText(text).then(() => {
    // Flash copy icon
    const copyIcon = document.getElementById(`copy-icon-${id}`);
    if (copyIcon) {
      copyIcon.setAttribute("data-lucide", "check");
      copyIcon.style.color = "var(--color-approved)";
      lucide.createIcons();
      
      setTimeout(() => {
        copyIcon.setAttribute("data-lucide", "copy");
        copyIcon.style.color = "";
        lucide.createIcons();
      }, 1500);
    }
    
    showToast("Copied customer input to clipboard!", "success");
  }).catch(err => {
    console.error("Could not copy text: ", err);
    alert("Copy failed. Please manually select and copy.");
  });
};

// Export dataset with audit parameters
function exportDataset() {
  // Map currentScenarios with their audit state included for standard exports
  const exportedData = currentScenarios.map(s => ({
    ...s,
    audit_status: auditStates[s.id] || "unreviewed"
  }));

  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportedData, null, 2));
  const downloadAnchor = document.createElement("a");
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", "audited_user_scenarios_v1.json");
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();

  showToast("Exported audited JSON dataset!", "success");
}

// Custom Toast notification helper
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  
  let iconHTML = '<i data-lucide="check-circle-2"></i>';
  if (type === "info") {
    iconHTML = '<i data-lucide="info" style="color:var(--accent-color)"></i>';
  } else if (type === "danger") {
    iconHTML = '<i data-lucide="alert-triangle" style="color:var(--color-flagged)"></i>';
  }
  
  toast.innerHTML = `${iconHTML} <span>${message}</span>`;
  container.appendChild(toast);
  
  // Re-run lucide icons render
  lucide.createIcons();

  // Remove toast after animation finishes
  setTimeout(() => {
    toast.remove();
  }, 3000);
}
