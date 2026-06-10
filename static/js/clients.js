const container = document.getElementById("accounts-container");
const countInput = document.getElementById("account_count");
let accountIndex = 0;

function renderAccount(account = {}) {
  const idx = accountIndex++;
  const row = document.createElement("div");
  row.className = "account-row";
  row.innerHTML = `
    <label>Owner
      <select name="account_owner_${idx}">
        <option value="client1" ${account.owner === "client1" ? "selected" : ""}>Client 1</option>
        <option value="client2" ${account.owner === "client2" ? "selected" : ""}>Client 2</option>
        <option value="joint" ${account.owner === "joint" || !account.owner ? "selected" : ""}>Joint</option>
      </select>
    </label>
    <label>Category
      <select name="account_category_${idx}">
        <option value="retirement" ${account.category === "retirement" ? "selected" : ""}>Retirement</option>
        <option value="non_retirement" ${account.category === "non_retirement" ? "selected" : ""}>Non-Retirement</option>
        <option value="trust" ${account.category === "trust" ? "selected" : ""}>Trust</option>
        <option value="liability" ${account.category === "liability" ? "selected" : ""}>Liability</option>
      </select>
    </label>
    <label>Type <input type="text" name="account_type_${idx}" value="${account.account_type || ""}"></label>
    <label>Label <input type="text" name="account_label_${idx}" value="${account.label || ""}" required></label>
    <label>Last 4 <input type="text" name="account_last_four_${idx}" value="${account.last_four || ""}" maxlength="4"></label>
    <label>Interest Rate <input type="number" step="0.01" name="account_rate_${idx}" value="${account.interest_rate ?? ""}"></label>
    <label>Property Address <input type="text" name="account_property_${idx}" value="${account.property_address || ""}"></label>
    <button type="button" class="btn btn-secondary remove-account">Remove</button>
  `;
  row.querySelector(".remove-account").addEventListener("click", () => {
    row.remove();
    updateCount();
  });
  container.appendChild(row);
  updateCount();
}

function updateCount() {
  countInput.value = container.querySelectorAll(".account-row").length;
}

document.getElementById("add-account").addEventListener("click", () => renderAccount());

if (typeof existingAccounts !== "undefined" && existingAccounts.length) {
  existingAccounts.forEach(renderAccount);
} else {
  renderAccount({ owner: "client1", category: "retirement", account_type: "Roth IRA", label: "Roth IRA" });
}
