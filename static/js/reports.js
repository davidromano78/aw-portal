function money(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return "$" + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function collectPayload() {
  const balances = [];
  document.querySelectorAll(".account-balance").forEach((input) => {
    balances.push({
      account_id: Number(input.dataset.accountId),
      balance: parseFloat(input.value) || 0,
      cash_balance: null,
      as_of_date: null,
    });
  });

  return {
    client_id: CLIENT_ID,
    report: {
      report_date: document.querySelector('[name="report_date"]').value,
      status: document.querySelector('[name="status"]').value,
      inflow_balance: parseFloat(document.querySelector('[name="inflow_balance"]').value) || null,
      outflow_balance: parseFloat(document.querySelector('[name="outflow_balance"]').value) || null,
      private_reserve_balance: parseFloat(document.querySelector('[name="private_reserve_balance"]').value) || null,
      schwab_brokerage_balance: parseFloat(document.querySelector('[name="schwab_brokerage_balance"]').value) || null,
      balances,
    },
  };
}

async function refreshTotals() {
  try {
    const res = await fetch("/api/reports/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });
    if (!res.ok) return;
    const totals = await res.json();
    document.getElementById("total-excess").textContent = money(totals.excess);
    document.getElementById("total-target").textContent = money(totals.private_reserve_target);
    document.getElementById("total-c1").textContent = money(totals.c1_retirement_total);
    document.getElementById("total-c2").textContent = money(totals.c2_retirement_total);
    document.getElementById("total-nr").textContent = money(totals.nr_total);
    document.getElementById("total-trust").textContent = money(totals.trust_value);
    document.getElementById("total-grand").textContent = money(totals.grand_total);
    document.getElementById("total-liab").textContent = money(totals.liabilities_total);
  } catch (e) {
    console.error(e);
  }
}

document.querySelectorAll(".calc-field").forEach((el) => {
  el.addEventListener("input", refreshTotals);
});

document.querySelectorAll(".use-last").forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = document.getElementById(btn.dataset.target);
    if (target) {
      target.value = btn.dataset.value;
      refreshTotals();
    }
  });
});

refreshTotals();
