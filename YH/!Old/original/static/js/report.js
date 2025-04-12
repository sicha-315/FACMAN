// ✅ 전체 수정된 report.js
let gaugeCharts = {};
let lineCharts = {};
let fullReportData = [];

function updateClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleString("ko-KR", { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

function formatReportText(text) {
  return text.replace(/\n/g, "<br>");
}

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
  reportBox.innerHTML = "📄 보고서 생성 중...";

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
    production: !!document.getElementById("includeProduction")?.checked,
    downtime: !!document.getElementById("includeDowntime")?.checked,
    failureCount: !!document.getElementById("includeFailureCount")?.checked,
    mtbf: !!document.getElementById("includeMTBF")?.checked,
    mttr: !!document.getElementById("includeMTTR")?.checked
  };

  const rangeMap = {
    "1시간": "1h", "3시간": "3h", "6시간": "6h", "9시간": "9h"
  };

  let rangeParam = "";
  if (periodType === "weekly") {
    rangeParam = "7d";
  } else if (periodType === "monthly") {
    rangeParam = "31d";
  } else {
    if (rangeValue === "custom") {
      if (!startTime || !endTime) {
        alert("⛔ 시작 시간과 종료 시간을 모두 입력하세요.");
        return;
      }
      const formattedStart = startTime.length === 16 ? startTime + ":00+09:00" : startTime;
      const formattedEnd = endTime.length === 16 ? endTime + ":00+09:00" : endTime;
      rangeParam = `${formattedStart}/${formattedEnd}`;
    } else {
      rangeParam = rangeMap[rangeValue] || "1h";
    }
  }

  fetch("/generate_report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ processes, range: rangeParam, options: includeOptions })
  })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        reportBox.textContent = "❌ " + data.error;
        return;
      }

      data.reports = data.reports.map(rep => ({ ...rep, range: rangeParam }));
      fullReportData = data.reports;

      const tabs = document.getElementById("tabs");
      const chartsArea = document.getElementById("chartsArea");
      tabs.innerHTML = "";
      chartsArea.innerHTML = "";

      let fullSummary = "";

      data.reports.forEach((rep, idx) => {
        const tabBtn = document.createElement("div");
        tabBtn.className = "tab";
        tabBtn.textContent = rep.process;
        if (idx === 0) tabBtn.classList.add("active");
        tabBtn.dataset.target = `tab-${rep.process}`;
        tabs.appendChild(tabBtn);

        tabBtn.addEventListener("click", () => {
          document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
          document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
          tabBtn.classList.add("active");
          document.getElementById(`tab-${rep.process}`).classList.add("active");
        });

        const content = document.createElement("div");
        content.className = "tab-content";
        content.id = `tab-${rep.process}`;
        if (idx === 0) content.classList.add("active");

        const summaryBox = document.createElement("div");
        summaryBox.style.whiteSpace = "pre-wrap";
        summaryBox.innerHTML = `
          <h4 class="report-subtitle">📘 ${rep.process} 보고서</h4>
          <p><strong>📅 분석 기간:</strong> ${rep.range}</p>
          <p>${formatReportText(rep.report)}</p>
        `;
        content.appendChild(summaryBox);

        // ✅ 이후 모든 조건부 차트는 이 content 내부에 추가
        if (includeOptions.availability && rep.available) {
          const gaugeCanvas = document.createElement("canvas");
          gaugeCanvas.width = 200;
          gaugeCanvas.height = 200;
          drawGaugeChart(gaugeCanvas, rep.available, rep.process);
          content.appendChild(gaugeCanvas);
        }

        if (includeOptions.production && rep.production) {
          const prod = rep.production;
          const prodBox = document.createElement("div");
          prodBox.innerHTML = `
            <p>투입량: ${prod.input} / 산출량: ${prod.output} / 생산실적률: ${prod.rate}%</p>
          `;
          content.appendChild(prodBox);
        }

        if (includeOptions.failureCount && rep.failures) {
          const canvas = document.createElement("canvas");
          canvas.width = 400;
          canvas.height = 300;
          drawLineChart(canvas, rep.labels, rep.failures, rep.process);
          content.appendChild(canvas);
        }

        chartsArea.appendChild(content);
        fullSummary += `<br><br><strong>📌 [${rep.process}] 공정</strong><br><strong>📅 분석 기간:</strong> ${rep.range}<br>${formatReportText(rep.report)}`;
      });

      reportBox.innerHTML = fullSummary;
    })
    .catch(err => {
      reportBox.textContent = "❌ 보고서 생성 실패";
      console.error("Error while generating report:", err);
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


function drawDowntimePieChart(canvas, failure) {
  const total = failure > 0 ? failure : 1;  
  new Chart(canvas.getContext("2d"), {
    type: "pie",
    data: {
      labels: ["고장 다운타임", "기타"],
      datasets: [{
        data: [failure, total - failure],
        backgroundColor: ["#ff6666", "#66ccff"]
      }]
    },
    options: {
      responsive: false,
      plugins: {
        title: {
          display: true,
          text: "다운타임 유형별 비율"
        },
        legend: { position: "bottom" }
      }
    }
  });
}

function drawDowntimeBarChart(canvas, labels, failureData, repairData) {
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
          label: "수리",
          data: repairData,
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

function drawMTBFPieChart(canvas, mtbf, total) {
  new Chart(canvas.getContext("2d"), {
    type: "pie",
    data: {
      labels: ["MTBF", "기타 운영시간"],
      datasets: [{
        data: [mtbf, total - mtbf],
        backgroundColor: ["#28a745", "#dddddd"]
      }]
    },
    options: {
      responsive: false,
      plugins: {
        title: {
          display: true,
          text: "MTBF"
        },
        legend: {
          position: "bottom"
        }
      }
    }
  });
}

function drawMTTRPieChart(canvas, mttr, totalRepair) {
  new Chart(canvas.getContext("2d"), {
    type: "pie",
    data: {
      labels: ["MTTR", "기타 수리시간"],
      datasets: [{
        data: [mttr, totalRepair - mttr],
        backgroundColor: ["#ffa500", "#ddd"]
      }]
    },
    options: {
      responsive: false,
      plugins: {
        title: {
          display: true,
          text: "MTTR 시각화"
        },
        legend: {
          position: "bottom"
        }
      }
    }
  });
}
async function waitForCanvasRendered(canvasId, timeout = 2000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const canvas = document.getElementById(canvasId);
    if (canvas && canvas.getContext("2d").__chart__) return canvas; // Chart.js 객체 생성 확인
    await new Promise(res => setTimeout(res, 100));
  }
  return null;
}

// ✅ Docx 파일 다운로드
async function downloadDocx() {
  if (!fullReportData || fullReportData.length === 0) {
    alert("⚠️ 먼저 보고서를 생성하세요.");
    return;
  }

  const formData = new FormData();

  // 1. 전체 요약 텍스트 생성
  let combinedReport = "";
  let combinedFailureLabels = [];
  let combinedFailureCounts = [];

  for (let rep of fullReportData) {
    combinedReport += `\n\n📌 [${rep.process}] 공정\n📅 분석 기간: ${rep.range}\n${rep.report}\n`;


    if (rep.failureLabels && rep.failureCounts) {
      combinedFailureLabels = combinedFailureLabels.concat(rep.failureLabels);
      combinedFailureCounts = combinedFailureCounts.concat(rep.failureCounts);
    }
  }

  // 2. 데이터 추가 (텍스트, 고장 테이블, 전체 reportData)
  formData.append("report", combinedReport);
  formData.append("failureLabels", JSON.stringify(combinedFailureLabels));
  formData.append("failureCounts", JSON.stringify(combinedFailureCounts));
  formData.append("reportData", JSON.stringify(fullReportData));  

  // 3. 서버로 전송
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

// ✅ 엑셀 다운로드 요청
async function downloadExcel() {
  console.log("📥 엑셀 다운로드 버튼 클릭됨");
  if (!fullReportData || fullReportData.length === 0) {
    alert("⚠️ 먼저 보고서를 생성하세요.");
    return;
  }

  const formData = new FormData();
  formData.append("reportData", JSON.stringify(fullReportData));
  console.log("📤 전송할 데이터", fullReportData);

  try {
    const res = await fetch("/generate_excel", {
      method: "POST",
      body: formData,
    });

    console.log("📩 서버 응답", res);

    if (!res.ok) {
      alert("❌ 엑셀 파일 다운로드 실패");
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "제조_기초데이터.xlsx";
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    alert("❌ 다운로드 중 오류가 발생했습니다.");
    console.error("Excel download error:", error);
  }
}
