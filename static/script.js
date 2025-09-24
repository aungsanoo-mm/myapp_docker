let sum1 = 0, sum2 = 0, sum3 = 0, sum4 = 0, sum5 = 0, total = 0, incomeTotal = 0;

// Initialize chart only if canvas element exists
let expenseChart = null;
const chartCanvas = document.getElementById('expenseChart');

if (chartCanvas) {
    const ctx = chartCanvas.getContext('2d');
    expenseChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Foods', 'Clothes', 'Family', 'Health', 'Others'],
            datasets: [{
                label: 'Expense',
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    '#3e95cd',
                    '#ffa726', 
                    '#8e5ea2',
                    '#3cba9f',
                    '#f4c430'
                ],
                borderWidth: 2,
                borderColor: '#333'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    position: 'bottom',
                    labels: {
                        color: '#fff',
                        padding: 20
                    }
                },
                title: { 
                    display: true, 
                    text: 'Monthly Expense Chart',
                    color: '#fff',
                    font: {
                        size: 16
                    }
                }
            }
        }
    });
}

function updateChart() {
    if (expenseChart) {
        expenseChart.data.datasets[0].data = [sum1, sum2, sum3, sum4, sum5];
        expenseChart.update();
    }
}

function updateTable(data, dayTotal, isAdmin = false) {
    const tableBody = document.querySelector("#expense-table tbody");
    if (!tableBody) return;

    const row = document.createElement("tr");
    row.innerHTML = `
        <td>${data.date}</td>
        <td>${data.details}</td>
        <td>${data.cat1}</td>
        <td>${data.cat2}</td>
        <td>${data.cat3}</td>
        <td>${data.cat4}</td>
        <td>${data.cat5}</td>
        <td><strong>${dayTotal.toFixed(2)}</strong></td>
        <td>${data.remarks}</td>
        <td class="text-success">${data.income}</td>
        ${isAdmin ? `<td><span class="badge bg-primary">${data.username || 'Unknown'}</span></td>` : ''}
    `;
    tableBody.appendChild(row);

    // Update totals
    const elements = {
        sum1: document.getElementById("sum1"),
        sum2: document.getElementById("sum2"),
        sum3: document.getElementById("sum3"),
        sum4: document.getElementById("sum4"),
        sum5: document.getElementById("sum5"),
        sumTotal: document.getElementById("sumTotal"),
        sumIncome: document.getElementById("sumIncome")
    };

    if (elements.sum1) elements.sum1.innerText = sum1.toFixed(2);
    if (elements.sum2) elements.sum2.innerText = sum2.toFixed(2);
    if (elements.sum3) elements.sum3.innerText = sum3.toFixed(2);
    if (elements.sum4) elements.sum4.innerText = sum4.toFixed(2);
    if (elements.sum5) elements.sum5.innerText = sum5.toFixed(2);
    if (elements.sumTotal) elements.sumTotal.innerHTML = `<strong>${total.toFixed(2)}</strong>`;
    if (elements.sumIncome) elements.sumIncome.innerHTML = `<strong>${incomeTotal.toFixed(2)}</strong>`;
}

// Load expenses on page load
window.addEventListener("DOMContentLoaded", () => {
    const expenseTable = document.getElementById('expense-table');
    if (!expenseTable) return; // Don't load if not on dashboard

    fetch("/api/expense")
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(expenses => {
            // Check if user is admin by looking at table headers
            const isAdmin = document.querySelector('#expense-table thead th:last-child')?.textContent === 'User';
            
            expenses.forEach(data => {
                const dayTotal = data.cat1 + data.cat2 + data.cat3 + data.cat4 + data.cat5;
                sum1 += data.cat1;
                sum2 += data.cat2;
                sum3 += data.cat3;
                sum4 += data.cat4;
                sum5 += data.cat5;
                total += dayTotal;
                incomeTotal += data.income;
                updateTable(data, dayTotal, isAdmin);
            });
            updateChart();
        })
        .catch(error => {
            console.error("Error loading expenses:", error);
            // Show user-friendly error message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger alert-dismissible fade show';
            alertDiv.innerHTML = `
                Error loading expenses. Please refresh the page or try again later.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.dashboard-header').nextSibling);
        });
});

// Handle expense form submission
const expenseForm = document.getElementById("expense-form");
if (expenseForm) {
    expenseForm.addEventListener("submit", function(e) {
        e.preventDefault();

        const submitButton = this.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;
        
        // Show loading state
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Adding...';
        submitButton.disabled = true;

        const data = {
            date: document.getElementById("date").value,
            details: document.getElementById("details").value,
            cat1: parseFloat(document.getElementById("cat1").value) || 0,
            cat2: parseFloat(document.getElementById("cat2").value) || 0,
            cat3: parseFloat(document.getElementById("cat3").value) || 0,
            cat4: parseFloat(document.getElementById("cat4").value) || 0,
            cat5: parseFloat(document.getElementById("cat5").value) || 0,
            remarks: document.getElementById("remarks").value || '',
            income: parseFloat(document.getElementById("income").value) || 0
        };

        const dayTotal = data.cat1 + data.cat2 + data.cat3 + data.cat4 + data.cat5;

        // Update locally first for immediate feedback
        sum1 += data.cat1;
        sum2 += data.cat2;
        sum3 += data.cat3;
        sum4 += data.cat4;
        sum5 += data.cat5;
        total += dayTotal;
        incomeTotal += data.income;
        
        // Check if user is admin
        const isAdmin = document.querySelector('#expense-table thead th:last-child')?.textContent === 'User';
        updateTable(data, dayTotal, isAdmin);
        updateChart();

        // Submit to backend
        fetch("/api/expense", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        })
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(response => {
            console.log(response.message);
            // Show success message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success alert-dismissible fade show';
            alertDiv.innerHTML = `
                Expense added successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.dashboard-header').nextSibling);
            
            // Auto-dismiss after 3 seconds
            setTimeout(() => {
                alertDiv.remove();
            }, 3000);
        })
        .catch(error => {
            console.error("Backend error:", error);
            // Revert local changes on error
            sum1 -= data.cat1;
            sum2 -= data.cat2;
            sum3 -= data.cat3;
            sum4 -= data.cat4;
            sum5 -= data.cat5;
            total -= dayTotal;
            incomeTotal -= data.income;
            
            // Remove the row that was added
            const lastRow = document.querySelector("#expense-table tbody tr:last-child");
            if (lastRow) lastRow.remove();
            
            // Update totals and chart
            updateTable({cat1: 0, cat2: 0, cat3: 0, cat4: 0, cat5: 0}, 0);
            updateChart();
            
            // Show error message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger alert-dismissible fade show';
            alertDiv.innerHTML = `
                Failed to add expense. Please try again.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.dashboard-header').nextSibling);
        })
        .finally(() => {
            // Reset button state
            submitButton.innerHTML = originalText;
            submitButton.disabled = false;
        });

        // Reset form
        this.reset();
        
        // Set today's date as default
        const today = new Date().toISOString().split('T')[0];
        document.getElementById("date").value = today;
    });
    
    // Set today's date as default when page loads
    const today = new Date().toISOString().split('T')[0];
    document.getElementById("date").value = today;
}

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert:not(.alert-dismissible)');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});
