// 페이지 로드 후 차트를 그리기 위한 함수
function updateUsefulnessCharts(labels, availability) {
  const chartCtx = document.getElementById("usefulnessChart").getContext("2d");
  const avgAvailability = Math.round(
    (availability.reduce((a, b) => a + b, 0) / availability.length) * 100
  );

  const chart = new Chart(chartCtx, {
    type: "doughnut",
    data: {
      labels: ["가동률", "비가동률"],
      datasets: [
        {
          data: [avgAvailability, 100 - avgAvailability],
          backgroundColor: ["green", "#e0e0e0"],
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: { font: { size: 12 } },
        },
      },
      cutout: "50%",
    },
  });
}

// 서버 상태 업데이트를 위한 함수
function updateServerStatus(status) {
  const statusBox = document.getElementById("P1-A_status");
  const statusText = document.getElementById("serverStatusText");

  // 상태에 맞는 색상 및 텍스트 업데이트
  const statusMap = {
    "processing": "#4CAF50", // green
    "repair": "orange",      // orange
    "failure": "red",        // red
    "maintenance": "yellow", // yellow
  };

  if (statusBox) {
    statusBox.style.backgroundColor = statusMap[status] || "#444"; // 상태 색상
    statusText.textContent = status; // 서버 상태 텍스트
  }
}

// 유용성 데이터 받아오기
function fetchUsefulnessData() {
  const process = "P1-A"; // 예시: P1-A 공정에 대한 유용성 데이터
  const range = "1d"; // 예시: 지난 1일간의 데이터

  fetch("/get_usefulness_data", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ process, range }),
  })
    .then((res) => res.json())
    .then((data) => {
      // 유용성 차트 업데이트
      updateUsefulnessCharts(data.labels, data.availability);
      // 서버 상태 업데이트
      updateServerStatus(data.serverStatus); // 예: "processing", "repair", "failure", "maintenance"
    })
    .catch((err) => console.error("유용성 데이터 가져오기 실패:", err));
}

// 시간을 업데이트하는 함수
function updateClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleString("ko-KR", {
    hour12: false,
  });
}

// 페이지 로드 시 유용성 데이터 호출 및 시간 업데이트
window.onload = function () {
  fetchUsefulnessData(); // 유용성 데이터 호출
  updateClock(); // 시간 표시
  setInterval(updateClock, 1000); // 1초마다 시간 갱신
};
