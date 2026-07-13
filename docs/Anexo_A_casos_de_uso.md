# Diagrama de Casos de Uso — Sistema de Gestión de Arrocera

> Actores derivados de los roles reales del sistema (`init_db.py` →
> `_seed_roles_and_permissions`) y casos de uso derivados de las rutas Flask
> (`routes_*.py`). Renderiza con la vista previa de Mermaid de VSCode.

## Actores

| Actor | Rol en el sistema | Acceso |
|-------|-------------------|--------|
| **Superadmin** | `superadmin` | Acceso total al sistema |
| **Dueño del Lote** | `duenio_lote` | Acceso completo a su(s) lote(s) |
| **Administrador de Lote** | `admin_lote` | Gestión operativa + eliminación/configuración |
| **Operador de Lote** | `operador_lote` | Crear/editar recibos, trabajadores, cosechas |
| **Usuario de Consulta** | `consulta_lote` | Solo lectura |
| **Visitante** | (no autenticado) | Registro / login / aceptar invitación |
| **Sensor de Humedad** | dispositivo externo | Envía lecturas (`/humedad/api/ingest`) |
| **Asistente IA** | sistema externo | Asiste en chat y creación de lotes |
| **Servicio de Correo** | sistema externo | Envía códigos e invitaciones |

## Diagrama

```mermaid
flowchart LR
  %% ===== Actores =====
  SA([Superadmin])
  Duenio([Dueño del Lote])
  Admin([Administrador de Lote])
  Operador([Operador de Lote])
  Consulta([Usuario de Consulta])
  Visitante([Visitante])
  Sensor([Sensor de Humedad])
  IA([Asistente IA])
  Mail([Servicio de Correo])

  %% ===== Herencia entre actores =====
  SA -->|hereda| Duenio
  Duenio -->|hereda| Admin
  Admin -->|hereda| Operador
  Operador -->|hereda| Consulta

  subgraph SIS[Sistema de Gestión de Arrocera]
    direction TB

    subgraph AUTH[Autenticación y Cuenta]
      UCsignup(Registrarse)
      UCverify(Verificar código)
      UClogin(Iniciar sesión)
      UCforgot(Recuperar contraseña)
      UCvemail(Verificar correo)
      UClogout(Cerrar sesión)
    end

    subgraph LOTE[Gestión de Lotes]
      UCsetup(Crear lote con asistente IA)
      UCsellote(Seleccionar lote)
      UCinvite(Invitar usuarios)
      UCroles(Asignar roles)
      UCaccept(Aceptar invitación)
    end

    subgraph WORK[Trabajadores]
      UCwview(Ver trabajadores)
      UCwcreate(Registrar trabajador)
      UCwedit(Editar trabajador)
      UCwtoggle(Activar / Desactivar)
    end

    subgraph REC[Recibos]
      UCrview(Ver recibos)
      UCrcreate(Crear recibo)
      UCrlabores(Registrar labores)
      UCredit(Editar recibo)
      UCrdelete(Eliminar recibo)
      UCrconcilia(Conciliar recibos)
    end

    subgraph PROD[Producción]
      UCpview(Ver producción)
      UCpcreate(Registrar cosecha)
    end

    subgraph FIN[Finanzas]
      UCpresu(Gestionar presupuesto)
      UCahorro(Gestionar ahorro)
    end

    subgraph REP[Reportes]
      UCrepview(Ver reportes)
      UCexport(Exportar PDF/Excel/TXT)
    end

    subgraph HUM[Humedad y Riego]
      UChview(Ver módulo de humedad)
      UChriego(Controlar riego)
      UChsensores(Configurar sensores)
      UChingest(Ingestar datos de sensor)
    end

    subgraph AI[Asistente IA]
      UCchat(Chatear con asistente)
      UCchathist(Ver / borrar historial)
    end

    UCconfig(Gestionar configuración)
  end

  %% ===== Visitante =====
  Visitante --> UCsignup
  Visitante --> UClogin
  Visitante --> UCforgot
  Visitante --> UCvemail
  Visitante --> UCaccept

  %% ===== Usuario de Consulta (solo lectura) =====
  Consulta --> UClogout
  Consulta --> UCsellote
  Consulta --> UCwview
  Consulta --> UCrview
  Consulta --> UCpview
  Consulta --> UCrepview
  Consulta --> UCexport
  Consulta --> UChview
  Consulta --> UCchat
  Consulta --> UCchathist

  %% ===== Operador =====
  Operador --> UCwcreate
  Operador --> UCwedit
  Operador --> UCrcreate
  Operador --> UCrlabores
  Operador --> UCredit
  Operador --> UCpcreate
  Operador --> UChriego
  Operador --> UChsensores
  Operador --> UCpresu
  Operador --> UCahorro

  %% ===== Administrador =====
  Admin --> UCwtoggle
  Admin --> UCrdelete
  Admin --> UCrconcilia
  Admin --> UCinvite
  Admin --> UCconfig

  %% ===== Dueño del Lote =====
  Duenio --> UCsetup
  Duenio --> UCroles

  %% ===== include / extend =====
  UCsignup -. include .-> UCverify
  UClogin -. include .-> UCsellote
  UCrlabores -. extend .-> UCrcreate
  UCexport -. extend .-> UCrepview
  UCinvite -. include .-> UCroles

  %% ===== Actores externos =====
  Sensor --> UChingest
  UCchat --> IA
  UCsetup --> IA
  UCsignup --> Mail
  UCinvite --> Mail
  UCforgot --> Mail
  UCvemail --> Mail
```

## Notas

- La **herencia entre actores** (flecha *hereda*) significa que cada actor
  superior dispone también de todos los casos de uso de los actores inferiores.
  Así, el *Dueño del Lote* puede hacer todo lo del *Administrador*, *Operador* y
  *Consulta*, más sus casos exclusivos.
- `<<include>>`: el caso base **siempre** ejecuta el incluido (p. ej. Registrarse
  incluye Verificar código).
- `<<extend>>`: el caso extensor ocurre **opcionalmente** (p. ej. Registrar
  labores extiende Crear recibo).
- Existe además la versión **PlantUML** (`diagrama_casos_de_uso.puml`), que
  produce un diagrama UML formal con la notación de óvalos y monigotes.
