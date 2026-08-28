var CONTROL_PRODUCTS = {
  '1.3.6.1.4.1.1916.2.251': 'NAC-A-20',
  '1.3.6.1.4.1.1916.2.252': 'IA-V',
  '1.3.6.1.4.1.1916.2.253': 'IA-A-20',
  '1.3.6.1.4.1.1916.2.254': 'IA-A-300',
  '1.3.6.1.4.1.1916.2.279': 'IA-A-25',
  '1.3.6.1.4.1.1916.2.280': 'IA-A-305',
  '1.3.6.1.4.1.1916.2.418': 'IA-Generic'
};

function normalizeOid(oid) {
  return String(oid || '').replace(/^\.+/, '');
}

function classifyControlProduct(oid) {
  return CONTROL_PRODUCTS[normalizeOid(oid)] || '';
}

function controlProductIdentity(oid) {
  return classifyControlProduct(oid) ? 1 : 0;
}
