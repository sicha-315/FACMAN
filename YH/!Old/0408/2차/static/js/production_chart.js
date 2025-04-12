document.addEventListener("DOMContentLoaded", async () => {
  const ctx = document.getElementById("productionChart").getContext("2d");

  try {
    const res = await fetch("/get_production_data", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
    const data = await res.json();

    const labels = [
      "09:00", "10:00", "11:00", "12:00", "13:00",
      "14:00", "15:00", "16:00", "17:00", "18:00"
    ];

    const colors = {
      "P1-A": "#4CAF50",
      "P1-B": "#FFC107",
      "P2-A": "#2196F3",
      "P2-B": "#F44336"
    };

    const datasets = Object.keys(colors).map((line) => ({
      label: line,
      data: data[line] || Array(labels.length).fill(0),
      borderColor: colors[line],
      backgroundColor: colors[line],
      fill: false,
      tension: 0.3,
      borderWidth: 2,
      spanGaps: true
    }));

    new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: true,
            position: "top"
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        },
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "시간대"
            },
            ticks: {
              autoSkip: false
            }
          },
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "생산 수량"
            },
            ticks: {
              stepSize: 5,    // ✅ Y축 눈금 간격을 100 단위로
              callback: function(value) {
                return value.toString();  // 정수 형태로 라벨 표시
              }
            },
            suggestedMax: 20,   // ✅ 최대 값은 400으로 제안 (상황에 따라 조정 가능)
            grid: {
              drawBorder: true
            }
          }
        }
      }
    });

  } catch (error) {
    console.error("📉 생산 추이 로딩 실패:", error);
  }
});
