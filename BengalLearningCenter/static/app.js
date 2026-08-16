async function loadDashboard() {
  const response = await fetch('/api/dashboard');
  const data = await response.json();

  document.getElementById('total-students').textContent = data.stats.total_students;
  document.getElementById('staff-count').textContent = data.stats.staff_count;
  document.getElementById('present-staff').textContent = data.stats.present_staff;
  document.getElementById('pending-fees').textContent = data.stats.pending_fees;

  renderStaffAttendance(data.attendance.staff);
  renderStudentAttendance(data.attendance.students);
  renderNotices(data.notices);
  renderFees(data.fees);
  renderBillingSummary(data.billing_summary);
  populateStudentSelect(data.fees);
}

function renderStaffAttendance(staff) {
  const list = document.getElementById('staff-attendance-list');
  list.innerHTML = staff.map(member => `
    <div class="attendance-row">
      <div class="attendance-info">
        <strong>${member.name}</strong>
        <span>${member.role}</span>
      </div>
      <div class="attendance-meta">
        <div>${member.time}</div>
        <span class="badge ${member.status.toLowerCase()}">${member.status}</span>
      </div>
    </div>
  `).join('');
}

function renderStudentAttendance(students) {
  const list = document.getElementById('student-attendance-list');
  list.innerHTML = students.map(item => `
    <div class="student-row">
      <div>
        <strong>${item.class_name}</strong>
        <div>${item.present} present / ${item.absent} absent</div>
      </div>
      <div>
        <div class="progress"><span style="width:${item.attendance_rate}%"></span></div>
        <small>${item.attendance_rate}%</small>
      </div>
    </div>
  `).join('');
}

function renderNotices(notices) {
  const list = document.getElementById('notices-list');
  list.innerHTML = notices.map(notice => `
    <div class="notice-item">
      <strong>${notice.title}</strong>
      <div>${notice.message}</div>
      <div class="notice-meta">${notice.category} • ${notice.date}</div>
    </div>
  `).join('');
}

function renderFees(fees) {
  const list = document.getElementById('fees-list');
  list.innerHTML = fees.map(item => `
    <div class="fee-item">
      <div>
        <strong>${item.student}</strong>
        <small>${item.class_name}</small>
      </div>
      <div>
        <div>${item.tuition + item.transport + item.exam}</div>
        <span class="badge ${item.status.toLowerCase().replace(' ', '-')}">${item.status}</span>
      </div>
    </div>
  `).join('');
}

function renderBillingSummary(summary) {
  const container = document.getElementById('billing-summary');
  container.innerHTML = `
    <div class="metric-box">
      <span>Monthly income</span>
      <strong>৳ ${summary.monthly_income.toLocaleString()}</strong>
    </div>
    <div class="metric-box">
      <span>Pending collection</span>
      <strong>৳ ${summary.pending_collection.toLocaleString()}</strong>
    </div>
  `;
}

function populateStudentSelect(fees) {
  const select = document.getElementById('student-select');
  select.innerHTML = fees.map(item => `<option value="${item.student}">${item.student}</option>`).join('');
}

document.getElementById('payment-form').addEventListener('submit', async function (event) {
  event.preventDefault();

  const student = document.getElementById('student-select').value;
  const amount = Number(document.getElementById('payment-amount').value);

  if (!student || !amount) {
    alert('Please select a student and enter a valid amount.');
    return;
  }

  const response = await fetch('/api/fees/pay', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student, amount }),
  });

  const result = await response.json();
  if (response.ok) {
    alert(result.message);
    loadDashboard();
    document.getElementById('payment-form').reset();
  } else {
    alert(result.message || 'Payment failed.');
  }
});

loadDashboard();
