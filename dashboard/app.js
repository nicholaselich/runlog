const API_BASE = "/v1";
const METERS_PER_MILE = 1609.344;
let weeklyChart;
let distanceUnit = localStorage.getItem("runlog-distance-unit") || "mi";
let chartView = "weekly";
let weeklyData = [];
let monthlyData = [];

const $ = (id) => document.getElementById(id);

function toISODate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setDefaultDates() {
  const today = new Date();
  const start = new Date(today);
  start.setDate(start.getDate() - 83);
  $("date-from").value = toISODate(start);
  $("date-to").value = toISODate(today);
}

function distanceValue(meters) {
  return Number(meters || 0) / (distanceUnit === "mi" ? METERS_PER_MILE : 1000);
}

function unitLabel() {
  return distanceUnit === "mi" ? "mi" : "km";
}

function formatDistance(meters) {
  return distanceValue(meters).toLocaleString(undefined, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds || 0)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, "0")}m`;
  return `${minutes}m`;
}

function formatClock(seconds) {
  const total = Math.max(0, Math.round(Number(seconds || 0)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remainder = total % 60;
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`
    : `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function formatPace(movingSeconds, distanceMeters) {
  if (!distanceMeters || distanceMeters <= 0) return "—";
  const secondsPerUnit = movingSeconds / distanceValue(distanceMeters);
  const roundedSeconds = Math.round(secondsPerUnit);
  const minutes = Math.floor(roundedSeconds / 60);
  const seconds = roundedSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function formatDate(value) {
  const date = new Date(value);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

async function fetchJSON(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (_) { /* Keep the HTTP status message. */ }
    throw new Error(detail);
  }
  return response.json();
}

function updateSummary(weeks) {
  const totals = weeks.reduce((sum, week) => ({
    runs: sum.runs + Number(week.runs || 0),
    distance: sum.distance + Number(week.distance_m || 0),
    moving: sum.moving + Number(week.moving_time_s || 0),
  }), { runs: 0, distance: 0, moving: 0 });

  $("total-distance").textContent = formatDistance(totals.distance);
  $("total-distance-unit").textContent = unitLabel().toUpperCase();
  $("total-runs").textContent = totals.runs.toLocaleString();
  $("total-time").textContent = formatDuration(totals.moving);
  $("average-distance").textContent = totals.runs > 0
    ? formatDistance(totals.distance / totals.runs)
    : "—";
  $("average-distance-unit").textContent = `${unitLabel().toUpperCase()} / RUN`;

  const best = weeks.reduce((current, week) =>
    Number(week.distance_m || 0) > Number(current?.distance_m || 0) ? week : current, null);
  $("best-week").textContent = best && Number(best.distance_m) > 0 ? `${formatDistance(best.distance_m)}` : "0.0";
  $("best-week-unit").textContent = unitLabel();
  $("best-week-caption").textContent = best && Number(best.distance_m) > 0
    ? `${formatDistance(best.distance_m)} ${unitLabel()} during the week of ${formatDate(best.week_start)}.`
    : "No runs recorded in this date range yet.";
}

function renderDistanceChart(data) {
  const isWeekly = chartView === "weekly";
  const canvas = $("weekly-chart");
  const labelKey = isWeekly ? "week_start" : "month_start";
  if (weeklyChart) weeklyChart.destroy();
  $("chart-title").textContent = isWeekly ? "Weekly mileage" : "Monthly mileage";
  $("chart-unit").innerHTML = `${unitLabel().toUpperCase()} <span> / ${isWeekly ? "WEEK" : "MONTH"}</span>`;
  weeklyChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.map((period) => {
        const date = new Date(`${period[labelKey]}T00:00:00`);
        return isWeekly
          ? date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
          : date.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
      }),
      datasets: [{
        data: data.map((period) => distanceValue(period.distance_m)),
        backgroundColor: data.map((period) => Number(period.distance_m || 0) > 0 ? "#fc6b32" : "#343a3f"),
        hoverBackgroundColor: "#ff895d",
        borderRadius: 5,
        borderSkipped: false,
        maxBarThickness: 42,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (context) => ` ${context.parsed.y.toFixed(2)} ${unitLabel()}` } },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#858e94", maxRotation: 0, autoSkip: true, maxTicksLimit: 8, font: { family: "DM Sans", size: 10 } },
          border: { display: false },
        },
        y: {
          beginAtZero: true,
          grid: { color: "rgba(145, 155, 161, .12)" },
          ticks: { color: "#858e94", padding: 9, font: { family: "DM Sans", size: 10 }, callback: (value) => `${value} ${unitLabel()}` },
          border: { display: false },
        },
      },
    },
  });
}

function renderRecentRuns(activities) {
  const body = $("recent-runs");
  $("recent-count").textContent = `${activities.length} MOST RECENT`;
  if (!activities.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty-state">No runs found yet. Once you add activities, they’ll show up here.</td></tr>';
    return;
  }

  body.innerHTML = activities.map((activity) => {
    const distance = Number(activity.distance_m || 0);
    const moving = Number(activity.moving_time_s || 0);
    const name = escapeHTML(activity.activity_type || "Run");
    const elevation = activity.elevation_gain_m == null
      ? "—"
      : `${Math.round(Number(activity.elevation_gain_m) * (distanceUnit === "mi" ? 3.28084 : 1)).toLocaleString()} ${distanceUnit === "mi" ? "ft" : "m"}`;
    const avgHR = activity.avg_heartrate == null ? "—" : `${Math.round(Number(activity.avg_heartrate))} bpm`;
    const maxHR = activity.max_heartrate == null ? "—" : `${Math.round(Number(activity.max_heartrate))} bpm`;
    return `<tr>
      <td><span class="activity-type">●</span>${name}</td>
      <td>${formatDate(activity.start_time)}</td>
      <td>${formatDistance(distance)} ${unitLabel()}</td>
      <td>${formatClock(moving)}</td>
      <td>${formatPace(moving, distance)} /${unitLabel()}</td>
      <td>${elevation}</td>
      <td><span class="heart-rate-values"><span>AVG ${avgHR}</span><span>MAX ${maxHR}</span></span></td>
    </tr>
    `;
  }).join("");
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

async function refreshDashboard() {
  const from = $("date-from").value;
  const to = $("date-to").value;
  const button = $("refresh-button");
  const message = $("dashboard-message");

  if (!from || !to) {
    message.textContent = "Choose both a start date and an end date.";
    message.className = "message error";
    return;
  }
  if (from > to) {
    message.textContent = "The start date can't be after the end date.";
    message.className = "message error";
    return;
  }

  button.disabled = true;
  button.innerHTML = '<span class="refresh-icon">↻</span> Loading…';
  message.textContent = "Refreshing your running stats…";
  message.className = "message";

  try {
    const params = new URLSearchParams({ from, to });
    const [weeks, months, activities] = await Promise.all([
      fetchJSON(`${API_BASE}/stats/weekly?${params}`),
      fetchJSON(`${API_BASE}/stats/monthly?${params}`),
      fetchJSON(`${API_BASE}/activities?limit=8&offset=0`),
    ]);

    weeklyData = weeks;
    monthlyData = months;
    updateSummary(weeks);
    renderDistanceChart(chartView === "weekly" ? weeklyData : monthlyData);
    renderRecentRuns(activities);
    const rangeDistance = weeks.reduce((sum, week) => sum + Number(week.distance_m || 0), 0);
    $("monthly-total").textContent = `${formatDistance(rangeDistance)} ${unitLabel()}`;
    const updatedAt = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    $("last-updated").textContent = `UPDATED ${updatedAt}`;
    message.textContent = `Updated just now · ${weeks.length} weeks in view`;
  } catch (error) {
    message.textContent = `Couldn't load dashboard data: ${error.message}. Check that the API is running, then refresh.`;
    message.className = "message error";
  } finally {
    button.disabled = false;
    button.innerHTML = '<span class="refresh-icon">↻</span> Refresh';
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const savedTheme = localStorage.getItem("runlog-theme") || "dark";
  applyTheme(savedTheme);
  $("theme-toggle").addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    localStorage.setItem("runlog-theme", nextTheme);
    applyTheme(nextTheme);
  });
  setDefaultDates();
  $("refresh-button").addEventListener("click", refreshDashboard);
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      chartView = button.dataset.view;
      document.querySelectorAll("[data-view]").forEach((item) => {
        const selected = item.dataset.view === chartView;
        item.classList.toggle("active", selected);
        item.setAttribute("aria-pressed", String(selected));
      });
      if (weeklyData.length || monthlyData.length) renderDistanceChart(chartView === "weekly" ? weeklyData : monthlyData);
    });
  });
  document.querySelectorAll("[data-unit]").forEach((button) => {
    button.addEventListener("click", () => {
      distanceUnit = button.dataset.unit;
      localStorage.setItem("runlog-distance-unit", distanceUnit);
      updateUnitControls();
      refreshDashboard();
    });
  });
  updateUnitControls();
  refreshDashboard();
});

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const button = $("theme-toggle");
  const toLight = theme === "dark";
  button.textContent = toLight ? "☼" : "☾";
  button.setAttribute("aria-label", `Switch to ${toLight ? "light" : "dark"} theme`);
  button.title = `Switch to ${toLight ? "light" : "dark"} theme`;
}


function updateUnitControls() {
  document.querySelectorAll("[data-unit]").forEach((button) => {
    const selected = button.dataset.unit === distanceUnit;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  $("average-distance-unit").textContent = `${unitLabel().toUpperCase()} / RUN`;
  if (weeklyData.length || monthlyData.length) renderDistanceChart(chartView === "weekly" ? weeklyData : monthlyData);
}
