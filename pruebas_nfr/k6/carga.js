// Pruebas de carga y rendimiento (RNF-03, RNF-04) con Grafana k6.
// Uso (PowerShell):
//   k6 run -e USUARIO=dorisbaltazar -e CLAVE=tu_clave -e PERFIL=carga pruebas_nfr/k6/carga.js
// PERFIL: humo (1 usuario, 30 s) | carga (hasta 20 usuarios, 3 min) | estres (hasta 80 usuarios, 4 min)
// Opcional: -e BASE=http://127.0.0.1:8000
import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE = __ENV.BASE || 'http://127.0.0.1:8000';
const PERFIL = __ENV.PERFIL || 'humo';

const perfiles = {
  humo:   { stages: [{ duration: '30s', target: 1 }] },
  // La clínica atiende 3-6 pacientes/hora: 20 usuarios simultáneos es un escenario muy superior al real.
  carga:  { stages: [{ duration: '30s', target: 10 }, { duration: '2m', target: 20 }, { duration: '30s', target: 0 }] },
  estres: { stages: [{ duration: '1m', target: 20 }, { duration: '2m', target: 80 }, { duration: '1m', target: 0 }] },
};

export const options = {
  stages: perfiles[PERFIL].stages,
  thresholds: {
    // RNF-03: operaciones habituales en menos de 3 segundos
    http_req_duration: ['p(95)<3000', 'avg<1000'],
    // Tasa de errores menor a 1 %
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99'],
  },
};

function iniciarSesion() {
  const pagina = http.get(`${BASE}/login/`);
  const m = pagina.body.match(/name="csrfmiddlewaretoken" value="([^"]+)"/);
  const token = m ? m[1] : '';
  const r = http.post(`${BASE}/login/`, {
    username: __ENV.USUARIO, password: __ENV.CLAVE, csrfmiddlewaretoken: token,
  }, { headers: { Referer: `${BASE}/login/` }, redirects: 0 });
  check(r, { 'login correcto (302)': (x) => x.status === 302 });
}

export default function () {
  iniciarSesion();
  const rutas = [
    ['Panel', '/panel/'],
    ['Pacientes', '/mascotas/'],
    ['Buscar paciente', '/mascotas/?q=a'],
    ['Propietarios', '/mascotas/propietarios/'],
    ['Citas', '/citas/'],
    ['Historiales', '/historiales/'],
    ['Inventario', '/inventario/'],
    ['IA - formulario', '/diagnostico/nuevo/'],
    ['Reporte pacientes', '/reportes/pacientes/'],
    ['Reporte citas', '/reportes/citas/'],
    ['Reporte inventario', '/reportes/inventario/'],
    ['Exportar CSV', '/reportes/pacientes/?formato=csv'],
  ];
  for (const [nombre, ruta] of rutas) {
    group(nombre, () => {
      const r = http.get(`${BASE}${ruta}`, { tags: { name: nombre } });
      check(r, { [`${nombre}: 200`]: (x) => x.status === 200, [`${nombre}: < 3 s`]: (x) => x.timings.duration < 3000 });
    });
    sleep(1);
  }
}
