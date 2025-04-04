let gaugeCharts = {};
let lineCharts = {};
let fullReportData = [];

function updateClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleString("ko-KR", { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

document.addEventListener("DOMContentLoaded", () => {
  const periodType = document.getElementById("periodType");
  const rangeSelect = document.getElementById("range");
  const startTime = document.getElementById("startTime");
  const endTime = document.getElementById("endTime");

  periodType?.addEventListener("change", function () {
    if (this.value === "daily") {
      rangeSelect.disabled = false;
      Array.from(rangeSelect.options).forEach(opt => {
        if (["1일", "7일", "31일"].includes(opt.text)) opt.style.display = "none";
        else opt.style.display = "";
      });
    } else {
      rangeSelect.disabled = true;
      startTime.style.display = "none";
      endTime.style.display = "none";
    }
  });

  rangeSelect?.addEventListener("change", function () {
    const isCustom = this.value === "custom";
    startTime.style.display = isCustom ? "inline-block" : "none";
    endTime.style.display = isCustom ? "inline-block" : "none";
  });
});

function generateReport() {
  const reportBox = document.getElementById("reportBox");
  reportBox.textContent = "📄 보고서 생성 중...";

  const checkboxes = document.querySelectorAll("#processCheckboxes input:checked");
  const processes = Array.from(checkboxes).map(cb => cb.value);
  const rangeValue = document.getElementById("range")?.value;
  const periodType = document.getElementById("periodType")?.value;
  const startTime = document.getElementById("startTime")?.value;
  const endTime = document.getElementById("endTime")?.value;

  if (processes.length === 0) {
    alert("✅ 공정을 선택하세요.");
    return;
  }

  const includeOptions = {
    availability: !!document.getElementById("includeAvailability")?.checked,
    productionSummary: !!document.getElementById("includeProduction")?.checked,
    failureCount: !!document.getElementById("includeFailureCount")?.checked,
    failureTime: !!document.getElementById("includeFailureTime")?.checked,
    mtbf: !!document.getElementById("includeMTBF")?.checked,
    mttr: !!document.getElementById("includeMTTR")?.checked,
    downtime: !!document.getElementById("includeDowntime")?.checked
  };

  const rangeMap = {
    "1시간": "1h",
    "3시간": "3h",
    "6시간": "6h",
    "9시간": "9h"
  };

  let rangeParam = "";
  let formattedStart = "";
  let formattedEnd = "";

  if (periodType === "weekly") {
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    formattedStart = sevenDaysAgo.toISOString().slice(0, 19) + "+09:00";
    formattedEnd = now.toISOString().slice(0, 19) + "+09:00";
    rangeParam = `${formattedStart}/${formattedEnd}`;
  } else if (periodType === "monthly") {
    const now = new Date();
    const thirtyOneDaysAgo = new Date(now.getTime() - 31 * 24 * 60 * 60 * 1000);
    formattedStart = thirtyOneDaysAgo.toISOString().slice(0, 19) + "+09:00";
    formattedEnd = now.toISOString().slice(0, 19) + "+09:00";
    rangeParam = `${formattedStart}/${formattedEnd}`;
  } else {
    if (rangeValue === "custom") {
      if (!startTime || !endTime) {
        alert("⛔ 시작 시간과 종료 시간을 모두 입력하세요.");
        return;
      }
      formattedStart = startTime.length === 16 ? startTime + ":00+09:00" : startTime;
      formattedEnd = endTime.length === 16 ? endTime + ":00+09:00" : endTime;
      rangeParam = `${formattedStart}/${formattedEnd}`;
    } else {
      rangeParam = rangeMap[rangeValue] || "1h";
    }
  }

  fetch("/generate_report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ processes, range: rangeParam, options: includeOptions }),
  })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        reportBox.textContent = "❌ " + data.error;
        return;
      }

      let resultText = "✅ 보고서 생성 완료\n";
      const chartsArea = document.getElementById("chartsArea");
      chartsArea.innerHTML = "";
      fullReportData = data.reports;

      const sheetTabs = document.createElement("div");
      sheetTabs.className = "sheet-tabs";
      chartsArea.appendChild(sheetTabs);

      const sheetContents = document.createElement("div");
      sheetContents.id = "sheet-contents";
      chartsArea.appendChild(sheetContents);

      data.reports.forEach(rep => {
        resultText += `\n\n📌 [${rep.process}] 공정\n${rep.report}\n`;

        const tabBtn = document.createElement("button");
        tabBtn.textContent = rep.process;
        tabBtn.onclick = () => showSheet(rep.process);
        sheetTabs.appendChild(tabBtn);

        const contentDiv = document.createElement("div");
        contentDiv.className = "sheet-content";
        contentDiv.id = `sheet-${rep.process}`;
        contentDiv.style.display = "none";

        contentDiv.innerHTML = `<h3>${rep.process} 공정</h3><p>${rep.report}</p>`;

        // 차트, 표 등 필요한 컨텐츠 여기에 추가 가능

        sheetContents.appendChild(contentDiv);
      });

      if (data.reports.length > 0) {
        showSheet(data.reports[0].process);
      }

      reportBox.textContent = resultText;
    })
    .catch(err => {
      reportBox.textContent = "❌ 보고서 생성 실패";
      console.error("Error while generating report:", err);
    });
}

function showSheet(sheetId) {
  const sheets = document.querySelectorAll(".sheet-content");
  sheets.forEach(sheet => {
    sheet.style.display = (sheet.id === `sheet-${sheetId}`) ? "block" : "none";
  });
  const tabs = document.querySelectorAll(".sheet-tabs button");
  tabs.forEach(tab => {
    tab.classList.remove("active");
    if (tab.textContent === sheetId) tab.classList.add("active");
  });
}


function drawGaugeChart(canvas, availableArray, processName) {
  const ctx = canvas.getContext("2d");
  const avg = Math.round((availableArray.reduce((a, b) => a + b, 0) / availableArray.length) * 100);
  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["가동률", "비가동률"],
      datasets: [{
        data: [avg, 100 - avg],
        backgroundColor: ["green", "#e0e0e0"]
      }]
    },
    options: {
      responsive: false,
      plugins: {
        legend: { display: true, position: "bottom" }
      },
      cutout: "50%"
    }
  });
}

function drawLineChart(canvas, labels, counts, processName) {
  const ctx = canvas.getContext("2d");
  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: `${processName} 고장 수`,
        data: counts,
        borderColor: "red",
        backgroundColor: "rgba(255,0,0,0.1)",
        tension: 0.3,
        fill: true
      }]
    },
    options: {
      responsive: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            stepSize: 1,
            callback: value => value + "건"
          }
        }
      }
    }
  });
}

function drawDowntimePieChart(canvas, failure, maintenance) {
  new Chart(canvas.getContext("2d"), {
    type: "pie",
    data: {
      labels: ["고장 다운타임", "유지보수 다운타임"],
      datasets: [{
        data: [failure, maintenance],
        backgroundColor: ["#ff6666", "#66ccff"]
      }]
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: "다운타임 유형별 비율"
        }
      }
    }
  });
}

function drawDowntimeBarChart(canvas, labels, failureData, maintenanceData) {
  new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "고장",
          data: failureData,
          backgroundColor: "rgba(255, 99, 132, 0.7)"
        },
        {
          label: "유지보수",
          data: maintenanceData,
          backgroundColor: "rgba(54, 162, 235, 0.7)"
        }
      ]
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: "시간대별 다운타임 분포"
        }
      },
      responsive: false,
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "다운타임 (분)"
          }
        }
      }
    }
  });
}

async function downloadDocx() {
  if (!fullReportData || fullReportData.length === 0) {
    alert("⚠️ 먼저 보고서를 생성하세요.");
    return;
  }

  const formData = new FormData();
  let combinedReport = "";
  let combinedFailureLabels = [];
  let combinedFailureCounts = [];

  for (let rep of fullReportData) {
    combinedReport += `\n\n📌 [${rep.process}] 공정\n${rep.report}\n`;

    if (rep.failureLabels && rep.failureCounts) {
      combinedFailureLabels = combinedFailureLabels.concat(rep.failureLabels);
      combinedFailureCounts = combinedFailureCounts.concat(rep.failureCounts);
    }

    const availCanvas = document.getElementById(`availabilityImage-${rep.process}`);
    const failCanvas = document.getElementById(`failureLineChart-${rep.process}`);

    if (availCanvas) {
      const blob = await new Promise(resolve => availCanvas.toBlob(resolve, "image/png"));
      formData.append("availabilityImages", blob, `${rep.process}_avail.png`);
    }
    if (failCanvas) {
      const blob = await new Promise(resolve => failCanvas.toBlob(resolve, "image/png"));
      formData.append("failureImages", blob, `${rep.process}_fail.png`);
    }
  }

  formData.append("report", combinedReport);
  formData.append("failureLabels", JSON.stringify(combinedFailureLabels));
  formData.append("failureCounts", JSON.stringify(combinedFailureCounts));

  const res = await fetch("/generate_docx", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    alert("❌ 보고서 다운로드 실패");
    return;
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "제조_보고서.docx";
  link.click();
  window.URL.revokeObjectURL(url);
}