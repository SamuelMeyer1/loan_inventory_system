// Run with: node tests/test_loan_cart.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const elements = new Map();
const get = (id) => {
  if (!elements.has(id)) elements.set(id, {
    value: '', textContent: '', innerHTML: '', disabled: false,
    classList: { remove() {} }, focus() {}, querySelectorAll: () => [],
  });
  return elements.get(id);
};
const calls = [];
let selected = [];
const context = vm.createContext({
  state: { language: 'en', loanCart: [], loans: [], objects: [
    { object_id: 'A', name: 'Same name', is_consumable: 0 },
    { object_id: 'B', name: 'Same name', is_consumable: 0 },
  ] },
  $: get,
  document: { querySelectorAll: (selector) => selector === '[data-return-select]:checked' ? selected : [] },
  escapeHtml: (text) => String(text),
  isConsumableObject: (item) => Boolean(item.is_consumable),
  resolveCheckoutUserId: () => 'user',
  showToast() {}, t: (key) => key,
  confirm: () => true,
  renderCheckoutUserDetails() {}, resetAutoUserCardScanMemory() {}, setDefaultDates() {},
  refreshAll: async () => {},
  api: async (url, options) => { calls.push({ url, payload: JSON.parse(options.body) }); return { request_id: 1 }; },
});
vm.runInContext(fs.readFileSync('frontend/js/loan-views.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('frontend/js/actions.js', 'utf8'), context);

async function main() {
  get('#checkoutObjectId').value = 'Same name';
  get('#checkoutObjectInstrumentId').value = 'B';
  get('#checkoutQuantity').value = '2';
  context.addLoanArticle();
  assert.equal(context.state.loanCart[0].object_id, 'B', 'Use selected ID when names are identical');
  get('#checkoutObjectId').value = 'A';
  get('#checkoutQuantity').value = '1';
  context.addLoanArticle();
  assert.equal(context.state.loanCart.length, 2);
  get('#checkoutObjectId').value = 'A';
  context.addLoanArticle();
  assert.equal(context.state.loanCart[1].quantity, 2, 'Repeated article merges quantities');
  await context.requestLoan();
  assert.equal(calls[0].payload.items.length, 2);
  assert.equal(calls[0].payload.user_id, 'user');
  assert.equal(context.state.loanCart.length, 0);
  const grouped = context.groupLoanRequestRows([
    { request_id: 11, request_group_id: 10, status: 'approved' },
    { request_id: 10, request_group_id: 10, status: 'requested' },
    { request_id: 12, request_group_id: 12, status: 'prepared' },
  ]);
  assert.equal(grouped.length, 2);
  assert.equal(grouped[0].status, 'requested', 'Group stays in earliest article status');
  assert.equal(grouped[0].partial, true);
  assert.equal(JSON.stringify(grouped[0].items.map((item) => item.request_id)), JSON.stringify([10, 11]));
  context.state.loanCart.push({ object_id: 'A', name: 'Same name', quantity: 1 });
  context.api = async () => { throw new Error('Request failed'); };
  await context.requestLoan();
  assert.equal(context.state.loanCart.length, 1, 'Failed request preserves cart');
  assert.equal(get('#requestLoanButton').disabled, false);
  context.api = async (url, options) => {
    const payload = JSON.parse(options.body);
    calls.push({ url, payload });
    return { items: payload.items || [], returned_quantity: 1, damaged_quantity: 0, remaining_quantity: 3 };
  };
  context.state.loans = [
    { loan_id: 1, user_id: 'user', quantity: 2, returned_quantity: 1, remaining_quantity: 1 },
    { loan_id: 2, user_id: 'other', quantity: 2 },
    { loan_id: 3, user_id: 'user', quantity: 4, returned_quantity: 0, remaining_quantity: 4 },
  ];
  for (const id of [1, 3]) {
    get(`[data-return-quantity="${id}"]`).value = '1';
    get(`[data-return-damaged="${id}"]`).value = '0';
    get(`[data-return-description="${id}"]`).value = '';
  }
  get('#returnUser').value = 'user';
  selected = [{ dataset: { returnSelect: '3' } }];
  await context.returnSelectedLoans();
  assert.deepEqual(calls.at(-1).payload.items.map((item) => item.loan_id), [3]);
  assert.equal(calls.at(-1).payload.items[0].quantity, 1);
  assert.equal(context.state.returnSummary.remaining_quantity, 3);
  await context.returnSelectedLoans(true);
  assert.deepEqual(calls.at(-1).payload.items.map((item) => item.loan_id), [1, 3], 'Return all is limited to selected user');
  assert.deepEqual(calls.at(-1).payload.items.map((item) => item.quantity), [1, 4], 'Return all uses remaining quantities');
  assert.equal(calls.at(-1).payload.items[0].expected_returned_quantity, 1);
  get('[data-return-damaged="3"]').value = '1';
  const beforeInvalid = calls.length;
  await context.returnSelectedLoans();
  assert.equal(calls.length, beforeInvalid, 'Damage requires explanation');
  get('[data-return-description="3"]').value = 'Cracked casing';
  await context.returnSelectedLoans();
  assert.equal(calls.at(-1).payload.items[0].damaged_quantity, 1);
  assert.equal(calls.at(-1).payload.items[0].damage_description, 'Cracked casing');
  context.state.returnBusy = true;
  const beforeBusy = calls.length;
  await context.returnSelectedLoans();
  assert.equal(calls.length, beforeBusy, 'Busy state prevents double submission');
  context.state.returnBusy = false;
  context.confirm = () => false;
  await context.returnSelectedLoans();
  assert.equal(calls.length, beforeBusy, 'Cancelled confirmation does not submit');
  context.confirm = () => true;
  context.state.role = 'operator';
  context.state.damagedReturns = [{ return_id: 10, damaged_quantity: 1, object_name: 'Tool' }];
  await context.resolveDamage(10, 'discarded');
  assert.equal(calls.length, beforeBusy, 'Operator cannot resolve damages');
  context.state.role = 'admin';
  context.formatTime = (value) => value || '';
  await context.resolveDamage(10, 'repaired');
  assert.equal(calls.at(-1).payload.resolution, 'repaired');
  assert.equal(calls.at(-1).payload.confirmed, true);
  console.log('Loan cart, partial return, validation, summary and damage-resolution checks passed.');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
