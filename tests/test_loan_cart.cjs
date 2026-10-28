// Run with: node tests/test_loan_cart.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const elements = new Map();
const get = (id) => {
  if (!elements.has(id)) elements.set(id, {
    value: '', textContent: '', innerHTML: '', disabled: false, dataset: {},
    classList: { remove() {}, contains: () => false }, focus() {}, querySelectorAll: () => [],
    handlers: {}, addEventListener(event, handler) { this.handlers[event] = handler; },
    closest: () => null,
  });
  return elements.get(id);
};
const calls = [];
const messages = [];
let selected = [];
const context = vm.createContext({
  state: { language: 'en', loanCart: [], loans: [], objects: [
    { object_id: 'A', name: 'Same name', is_consumable: 0, available_quantity: 15, total_quantity: 15 },
    { object_id: 'B', name: 'Same name', is_consumable: 0, available_quantity: 15, total_quantity: 15 },
  ], objectScanBusy: false, objectScanRequestId: null, objectScanToken: 0 },
  $: get,
  document: { querySelectorAll: (selector) => {
    if (selector === '[data-return-select]:checked') return selected;
    if (selector === '[data-cart-quantity]' || selector === '[data-cart-remove]') {
      const attribute = selector.slice(1, -1);
      return context.state.loanCart.map((entry, index) => {
        const input = get(`[${attribute}="${index}"]`);
        input.dataset[attribute === 'data-cart-quantity' ? 'cartQuantity' : 'cartRemove'] = String(index);
        input.value = String(entry.quantity);
        return input;
      });
    }
    return [];
  } },
  escapeHtml: (text) => String(text),
  isConsumableObject: (item) => Boolean(item.is_consumable),
  resolveCheckoutUserId: () => 'user',
  showToast: (message) => messages.push(message),
  t: (key, values = {}) => [key, ...Object.values(values)].join(' '),
  setTimeout: () => 1,
  statusText: (value) => value,
  confirm: () => true,
  renderCheckoutUserDetails() {}, resetAutoUserCardScanMemory() {}, setDefaultDates() {},
  refreshAll: async () => {},
  api: async (url, options) => {
    if (url === '/api/objects') return context.state.objects;
    calls.push({ url, payload: JSON.parse(options.body) }); return { request_id: 1 };
  },
});
vm.runInContext(fs.readFileSync('frontend/js/loan-views.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('frontend/js/actions.js', 'utf8'), context);

async function main() {
  const cameraPreference = new Map([['loanObjectScanPythonCameraIndex', '2']]);
  context.localStorage = {
    getItem: (key) => cameraPreference.get(key) || null,
    setItem: (key, value) => cameraPreference.set(key, String(value)),
  };
  context.state.objects.push({ object_id: 'OBJ-12345', name: 'Scanned object' });
  assert.equal(context.matchCheckoutObjectByScanCode('12345').item.object_id, 'OBJ-12345');
  context.scannedObjectId = '';
  vm.runInContext('selectCheckoutObject = (objectId) => { scannedObjectId = objectId; };', context);
  const loanApi = context.api;
  const scanRequests = [];
  context.api = async (url, options) => {
    scanRequests.push({ url, payload: JSON.parse(options.body) });
    return { code: '12345', cancelled: false };
  };
  await context.startObjectQrScan(++context.state.objectScanToken, 'scan-test-123');
  assert.deepEqual(scanRequests, [{
    url: '/api/objects/scan', payload: { camera_index: 2, scan_id: 'scan-test-123' },
  }]);
  assert.equal(context.scannedObjectId, 'OBJ-12345', get('#objectScanStatusText').textContent);
  context.api = loanApi;

  const detailsContext = vm.createContext({
    document: { querySelector: get },
    localStorage: { getItem: () => null },
    establishSession: async () => false,
  });
  vm.runInContext(fs.readFileSync('frontend/js/app.js', 'utf8'), detailsContext);
  const firstUser = { user_id: 'first', company: 'Test company', email: 'first@example.invalid' };
  const nextUser = { user_id: 'next', company: 'Other company' };
  const disclosure = get('#checkoutUserDisclosure');
  detailsContext.renderCheckoutUserDetails(firstUser);
  assert.equal(disclosure.hidden, false);
  assert.equal(disclosure.open, false, 'User information is collapsed on selection');
  assert.equal(get('#checkoutUserEmail').value, firstUser.email);
  disclosure.open = true;
  detailsContext.renderCheckoutUserDetails(firstUser);
  assert.equal(disclosure.open, true, 'Refreshing the same user preserves expansion');
  detailsContext.renderCheckoutUserDetails(nextUser);
  assert.equal(disclosure.open, false, 'Selecting a different user collapses extra information');
  assert.equal(get('#checkoutUserCompany').value, nextUser.company);
  assert.equal(get('#checkoutUserEmail').value, '', 'Missing details do not retain the previous user');
  disclosure.open = true;
  detailsContext.renderCheckoutUserDetails();
  assert.equal(disclosure.hidden, true, 'No disclosure without a selected user');
  assert.equal(disclosure.open, false);
  assert.equal(get('#checkoutUserCompany').value, '');

  const choose = (id, quantity) => {
    get('#checkoutObjectId').value = id;
    get('#checkoutObjectInstrumentId').value = id;
    context.updateCheckoutInfo();
    get('#checkoutQuantity').value = String(quantity);
  };
  choose('A', 16);
  assert.equal((get('#checkoutQuantity').innerHTML.match(/<option/g) || []).length, 15);
  assert.equal(get('#checkoutObjectQuantity').value, '15 of 15');
  assert.throws(() => context.addLoanArticle(), /stockExceeded.*15/);
  assert.equal(context.state.loanCart.length, 0);
  choose('A', 15);
  context.addLoanArticle();
  assert.equal(context.state.loanCart[0].quantity, 15);
  assert.match(get('#loanCart').innerHTML, /max="15"/);
  choose('A', 1);
  assert.equal(get('#checkoutObjectQuantity').value, '0 of 15');
  assert.equal(get('#checkoutObjectStatus').value, 'Slut');
  assert.equal(get('#checkoutQuantity').disabled, true);
  assert.match(get('#checkoutQuantity').innerHTML, /checkout.noneRemaining/);
  assert.equal(get('#addLoanArticle').disabled, true);
  assert.throws(() => context.addLoanArticle(), /stockExceeded.*0/);
  const cartInput = get('[data-cart-quantity="0"]');
  for (const invalid of [16, 0, -1, 1.5, '']) {
    cartInput.value = String(invalid);
    cartInput.handlers.change();
    assert.equal(context.state.loanCart[0].quantity, 15);
    assert.equal(cartInput.value, '15');
  }
  assert.ok(messages.some((message) => message.includes('stockExceeded')));
  cartInput.value = '10';
  cartInput.handlers.change();
  assert.equal(context.state.loanCart[0].quantity, 10);
  assert.equal(get('#checkoutObjectQuantity').value, '5 of 15');
  assert.equal((get('#checkoutQuantity').innerHTML.match(/<option/g) || []).length, 5);
  get('[data-cart-remove="0"]').handlers.click();
  assert.equal(get('#checkoutObjectQuantity').value, '15 of 15');
  assert.equal(context.state.objects[0].available_quantity, 15, 'Cart does not alter persisted stock');
  choose('A', 8);
  context.addLoanArticle();
  choose('A', 8);
  assert.throws(() => context.addLoanArticle(), /stockExceeded.*7/);
  assert.equal(context.state.loanCart[0].quantity, 8, 'Merging cannot exceed remaining stock');
  get('[data-cart-remove="0"]').handlers.click();
  context.state.objects[0].available_quantity = 0;
  choose('A', 1);
  assert.equal(get('#addLoanArticle').disabled, true);
  assert.throws(() => context.addLoanArticle(), /stockExceeded.*0/);
  context.state.objects[0].available_quantity = 15;
  choose('A', 10);
  context.addLoanArticle();
  const normalApi = context.api;
  let stalePost = false;
  context.api = async (url) => {
    if (url === '/api/objects') return context.state.objects.map((item) => ({...item, available_quantity: 9}));
    stalePost = true;
  };
  await context.requestLoan();
  assert.equal(stalePost, false, 'Fresh stock is validated before sending');
  assert.equal(context.state.loanCart[0].quantity, 10, 'Stale draft remains available for correction');
  assert.match(get('#loanCart').innerHTML, /max="9"/);
  assert.match(get('#loanCart').innerHTML, /aria-invalid="true"/);
  context.api = normalApi;
  context.state.objects.forEach((item) => { item.available_quantity = 15; });
  context.state.loanCart = [];
  context.renderLoanCart();

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
  get('#checkoutQuantity').value = '1';
  context.addLoanArticle();
  assert.equal(context.state.loanCart[1].quantity, 2, 'Repeated article merges quantities');
  await context.requestLoan();
  assert.equal(calls[0].payload.items.length, 2);
  assert.equal(calls[0].payload.user_id, 'user');
  assert.equal(context.state.loanCart.length, 0);
  const savedObjects = context.state.objects;
  context.state.objects = [
    { object_id: 'OBJ-1001', name: 'Torque wrench', available_quantity: 4, total_quantity: 4 },
    { object_id: 'OBJ-1005', name: 'USB cable', available_quantity: 8, total_quantity: 8 },
  ];
  context.state.objects.push({ object_id: 'OBJ-12345', name: 'Scanned item' });
  assert.equal(context.matchCheckoutObjectByScanCode('12345').item.object_id, 'OBJ-12345');
  assert.equal(context.matchCheckoutObjectByScanCode('OBJ-12345').item.object_id, 'OBJ-12345');
  context.state.objects.push({ object_id: 'ALT-12345', name: 'Duplicate suffix' });
  assert.equal(context.matchCheckoutObjectByScanCode('12345').ambiguous, true);
  assert.equal(context.matchCheckoutObjectByScanCode('unknown').item, null);
  context.state.loanCart = [
    { object_id: 'OBJ-1005', name: 'USB cable', quantity: 1 },
    { object_id: 'OBJ-1001', name: 'Torque wrench', quantity: 3 },
  ];
  choose('OBJ-1001', 1);
  context.renderLoanCart();
  const fullCartInput = get('[data-cart-quantity="1"]');
  fullCartInput.value = '4';
  fullCartInput.handlers.change();
  assert.equal(get('#checkoutQuantity').disabled, true);
  const beforeFullCart = calls.length;
  await context.requestLoan();
  assert.equal(calls.length, beforeFullCart + 1, 'A full 4-of-4 cart must submit even with the same article selected');
  assert.deepEqual(calls.at(-1).payload.items, [
    { object_id: 'OBJ-1005', quantity: 1 }, { object_id: 'OBJ-1001', quantity: 4 },
  ]);
  context.state.loanCart = [{ object_id: 'OBJ-1001', name: 'Torque wrench', quantity: 3 }];
  choose('OBJ-1001', 1);
  await context.requestLoan();
  assert.deepEqual(calls.at(-1).payload.items, [{ object_id: 'OBJ-1001', quantity: 3 }],
    'Sending preserves explicit cart quantity; adding more requires Add article');
  choose('OBJ-1001', 4);
  await context.requestLoan();
  assert.deepEqual(calls.at(-1).payload.items, [{ object_id: 'OBJ-1001', quantity: 4 }],
    'Single selected article still submits without manually adding it');
  context.state.loanCart = [{ object_id: 'OBJ-1005', name: 'USB cable', quantity: 1 }];
  choose('OBJ-1001', 2);
  await context.requestLoan();
  assert.deepEqual(calls.at(-1).payload.items, [
    { object_id: 'OBJ-1005', quantity: 1 }, { object_id: 'OBJ-1001', quantity: 2 },
  ], 'An unsaved different selection is still included');
  context.state.loanCart = [{ object_id: 'OBJ-1001', name: 'Torque wrench', quantity: 4 }];
  choose('OBJ-1001', 1);
  const beforeStockChange = calls.length;
  context.api = async (url) => url === '/api/objects'
    ? context.state.objects.map((item) => ({ ...item, available_quantity: 3 }))
    : calls.push({ url });
  await context.requestLoan();
  assert.equal(calls.length, beforeStockChange, 'A full selected cart still validates newly reduced stock');
  assert.equal(context.state.loanCart[0].quantity, 4);
  context.api = normalApi;
  context.state.loanCart = [];
  context.state.objects = savedObjects;
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
    if (url === '/api/objects') return context.state.objects;
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
  for (const prefix of ['return', 'job-return']) {
    const damaged = get(`[data-${prefix}-damaged="3"]`);
    const description = get(`[data-${prefix}-description="3"]`);
    const label = { hidden: false };
    description.closest = () => prefix === 'job-return' ? label : null;
    damaged.value = '1';
    context.syncReturnDamageDescription(prefix, 3);
    assert.equal(description.hidden, false);
    assert.equal(description.required, true);
    description.value = 'Old damage draft';
    damaged.value = '0';
    context.syncReturnDamageDescription(prefix, 3);
    assert.equal(description.hidden, true);
    assert.equal(description.required, false);
    assert.equal(description.value, '', 'Clearing damaged quantity removes the obsolete description');
    if (prefix === 'job-return') assert.equal(label.hidden, true);
    damaged.value = '2';
    context.syncReturnDamageDescription(prefix, 3);
    assert.equal(description.hidden, false);
    assert.equal(description.value, '');
    damaged.value = '0';
    context.syncReturnDamageDescription(prefix, 3);
  }
  await context.returnSelectedLoans();
  assert.equal(calls.at(-1).payload.items[0].damaged_quantity, 0);
  assert.equal(calls.at(-1).payload.items[0].damage_description, '');
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
