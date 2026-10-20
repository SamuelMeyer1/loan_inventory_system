// Run with: node tests/test_loan_cart.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const elements = new Map();
const get = (id) => {
  if (!elements.has(id)) elements.set(id, {
    value: '', textContent: '', innerHTML: '', disabled: false,
    classList: { remove() {} }, focus() {},
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
  context.api = async (url, options) => calls.push({ url, payload: JSON.parse(options.body) });
  context.state.loans = [{ loan_id: 1, user_id: 'user' }, { loan_id: 2, user_id: 'other' }, { loan_id: 3, user_id: 'user' }];
  get('#returnUser').value = 'user';
  selected = [{ dataset: { returnSelect: '3' } }];
  await context.returnSelectedLoans();
  assert.deepEqual(calls.at(-1).payload.loan_ids, [3]);
  await context.returnSelectedLoans(true);
  assert.deepEqual(calls.at(-1).payload.loan_ids, [1, 3], 'Return all is limited to selected user');
  console.log('Loan cart and return action checks passed.');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
