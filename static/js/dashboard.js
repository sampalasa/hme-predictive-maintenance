(function () {
    const CHART_COLORS = ["#2563eb", "#16a34a", "#ea580c", "#7c3aed", "#0d9488", "#dc2626"];

    function setKpiValues(kpis) {
        document.querySelectorAll("[data-kpi]").forEach(function (el) {
            const key = el.getAttribute("data-kpi");
            const suffix = el.getAttribute("data-suffix") || "";
            if (kpis[key] === undefined) return;
            el.textContent = kpis[key] + suffix;
        });
    }

    function renderAvailabilityGauge(availabilityPct) {
        const options = {
            chart: { type: "radialBar", height: 230 },
            series: [Math.max(0, Math.min(100, availabilityPct))],
            labels: ["Disponibilité"],
            colors: ["#16a34a"],
            plotOptions: {
                radialBar: {
                    hollow: { size: "60%" },
                    dataLabels: {
                        value: { fontSize: "1.6rem", fontWeight: 700, formatter: (v) => v + "%" },
                    },
                },
            },
        };
        new ApexCharts(document.querySelector("#gaugeAvailability"), options).render();
    }

    function renderFailuresByType(rows) {
        const ctx = document.getElementById("chartFailuresByType");
        if (!rows.length) {
            ctx.parentElement.insertAdjacentHTML("beforeend", '<p class="text-muted text-center">Aucune donnée</p>');
            return;
        }
        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: rows.map((r) => r.label),
                datasets: [{ data: rows.map((r) => r.count), backgroundColor: CHART_COLORS }],
            },
            options: { plugins: { legend: { position: "bottom" } } },
        });
    }

    function renderTopCritical(rows) {
        const ctx = document.getElementById("chartTopCritical");
        if (!rows.length) {
            ctx.parentElement.insertAdjacentHTML("beforeend", '<p class="text-muted text-center">Aucune donnée</p>');
            return;
        }
        new Chart(ctx, {
            type: "bar",
            data: {
                labels: rows.map((r) => r.equipment_code),
                datasets: [{ label: "Pannes", data: rows.map((r) => r.failures), backgroundColor: "#ef4444" }],
            },
            options: {
                indexAxis: "y",
                plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
            },
        });
    }

    function renderMonthlyEvolution(rows) {
        const options = {
            chart: { type: "area", height: 280, toolbar: { show: false } },
            series: [{ name: "Pannes", data: rows.map((r) => r.count) }],
            xaxis: { categories: rows.map((r) => r.month) },
            colors: ["#2563eb"],
            dataLabels: { enabled: false },
            stroke: { curve: "smooth", width: 2 },
            fill: { type: "gradient", gradient: { opacityFrom: 0.4, opacityTo: 0.05 } },
        };
        new ApexCharts(document.querySelector("#chartMonthlyEvolution"), options).render();
    }

    function renderRecentPredictions(rows) {
        const tbody = document.getElementById("tblRecentPredictions");
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center py-3">Aucune prédiction pour le moment</td></tr>';
            return;
        }
        tbody.innerHTML = rows
            .map(
                (r) => `<tr>
                    <td>${r.equipment_code}</td>
                    <td><span class="risk-badge risk-${r.risk_level}">${r.risk_level}</span></td>
                    <td>${(r.probability * 100).toFixed(1)}%</td>
                    <td>${new Date(r.created_at).toLocaleString("fr-FR")}</td>
                </tr>`
            )
            .join("");
    }

    function renderRecentMaintenance(rows) {
        const tbody = document.getElementById("tblRecentMaintenance");
        if (!rows.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center py-3">Aucune maintenance enregistrée</td></tr>';
            return;
        }
        tbody.innerHTML = rows
            .map(
                (r) => `<tr>
                    <td>${r.equipment_code}</td>
                    <td>${r.maintenance_type}</td>
                    <td>${r.downtime_hours}</td>
                    <td>${r.performed_by || "—"}</td>
                </tr>`
            )
            .join("");
    }

    fetch("/dashboard/api/data")
        .then((res) => {
            if (!res.ok) throw new Error("HTTP " + res.status);
            return res.json();
        })
        .then((data) => {
            setKpiValues(data.kpis);
            renderAvailabilityGauge(data.kpis.availability_pct);
            renderFailuresByType(data.failures_by_type);
            renderTopCritical(data.top_critical_equipment);
            renderMonthlyEvolution(data.monthly_evolution);
            renderRecentPredictions(data.recent_predictions);
            renderRecentMaintenance(data.recent_maintenance);
        })
        .catch((err) => {
            console.error("Dashboard load failed:", err);
            if (window.Swal) {
                Swal.fire({
                    icon: "error",
                    title: "Erreur de chargement",
                    text: "Impossible de charger les données du tableau de bord.",
                });
            }
        });
})();
