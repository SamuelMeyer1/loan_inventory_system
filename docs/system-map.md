# Loan Inventory System Map

This map is meant for learning the project. Read it like a PLC overview drawing:
browser screens are the operator panel, JavaScript is the panel logic, Python
services are the control logic, and SQLite is the memory/database.

## Big Picture

```mermaid
flowchart LR
    user[Operator / Admin / Super Admin]
    browser[Browser UI\nfrontend/index.html\nfrontend/styles.css]
    js[Frontend JavaScript\napp.js renders views\nactions.js handles forms\napi.js sends requests]
    server[Python HTTP Server\nbackend/server.py]
    services[Service Layer\nbackend/services/*.py]
    db[(SQLite Database\ndata/inventory.db)]
    external[External Notifications\nEmail / Teams]

    user --> browser
    browser --> js
    js -->|HTTP /api requests| server
    server -->|routes requests| services
    services -->|read/write| db
    services -->|optional messages| external
    services -->|JSON response| server
    server --> js
    js --> browser
```

## File Responsibilities

```mermaid
flowchart TB
    main[main.py\nstarts the app]
    server[backend/server.py\nserves frontend files\nhandles API routing]
    database[backend/database.py\nSQLite path\nschema setup\nmigrations]
    seed[backend/seed_data.py\ndefault/demo data]

    subgraph frontend[frontend]
        html[index.html\nUI shell]
        css[styles.css\nvisual layout]
        app[app.js\nstate and rendering]
        actions[actions.js\nbutton/form actions]
        api[api.js\nfetch helper]
        loanviews[loan-views.js\nloan/request views]
        charts[charts.js\nstatistics charts]
        i18n[i18n.js + translations.js\nSwedish/English text]
        utils[ui-utils.js + search.js\nsmall UI helpers]
    end

    subgraph backend[backend/services]
        inventory[inventory.py\nobjects and search]
        loans[loans.py\ncheckout, return, requests,\nconsumable reports, events]
        users[users.py\nusers and groups]
        stats[stats.py\ndashboard/statistics]
        notifications[notifications.py\nsettings, reminders,\nemail, Teams]
        common[common.py\nshared helpers]
        init[__init__.py\nexports service functions]
    end

    main --> server
    server --> init
    init --> inventory
    init --> loans
    init --> users
    init --> stats
    init --> notifications
    inventory --> common
    loans --> common
    users --> common
    stats --> common
    notifications --> common
    inventory --> database
    loans --> database
    users --> database
    stats --> database
    notifications --> database
    seed --> database

    html --> app
    html --> actions
    html --> api
    html --> loanviews
    html --> charts
    html --> i18n
    html --> utils
    app --> api
    actions --> api
```

## API To Service Map

```mermaid
flowchart TB
    frontend[Frontend JS\napp.js + actions.js + api.js]
    server[backend/server.py]

    frontend --> server

    server --> get[GET APIs]
    server --> post[POST APIs]
    server --> put[PUT APIs]
    server --> del[DELETE APIs]

    get --> g1[/api/stats -> stats.dashboard_stats/]
    get --> g2[/api/statistics -> stats.statistics_data/]
    get --> g3[/api/objects -> inventory.list_objects/]
    get --> g4[/api/search -> inventory.search_objects/]
    get --> g5[/api/users -> users.list_users/]
    get --> g6[/api/groups -> users.list_groups/]
    get --> g7[/api/loans -> loans.list_active_loans/]
    get --> g8[/api/loan-requests -> loans.list_loan_requests/]
    get --> g9[/api/consumable-reports -> loans.list_consumable_reports/]
    get --> g10[/api/events -> loans.recent_events/]
    get --> g11[/api/system-settings -> notifications.get_system_settings/]

    post --> p1[/api/checkout -> loans.checkout/]
    post --> p2[/api/issue -> loans.issue_item/]
    post --> p3[/api/return -> loans.return_item/]
    post --> p4[/api/objects -> inventory.add_object/]
    post --> p5[/api/users -> users.add_user/]
    post --> p6[/api/groups -> users.create_group/]
    post --> p7[/api/loan-requests -> loans.create_loan_request/]
    post --> p8[/api/consumable-reports -> loans.create_consumable_report/]
    post --> p9[/api/reminders/send -> notifications.send_loan_reminders/]
    post --> p10[/api/loans/reminder -> notifications.send_loan_reminder/]
    post --> p11[/api/loan-requests/pickup-email -> loans.send_pickup_ready_email/]
    post --> p12[/api/teams/test -> notifications.send_teams_test_message/]
    post --> p13[/api/users/card -> users.set_user_card/]
    post --> p14[/api/users/borrow-override -> users.set_user_borrow_override/]

    put --> u1[/api/objects -> inventory.update_object/]
    put --> u2[/api/users -> users.update_user/]
    put --> u3[/api/groups -> users.update_group/]
    put --> u4[/api/loan-requests -> loans.update_loan_request_status/]
    put --> u5[/api/loan-requests/details -> loans.update_loan_request_details/]
    put --> u6[/api/consumable-reports -> loans.close_consumable_report/]
    put --> u7[/api/system-settings -> notifications.update_system_settings/]

    del --> d1[/api/objects -> inventory.delete_object/]
    del --> d2[/api/users -> users.remove_user/]
    del --> d3[/api/groups -> users.delete_group/]
    del --> d4[/api/loan-requests -> loans.delete_loan_request/]
```

## Database Tables

```mermaid
erDiagram
    users ||--o{ loans : borrows
    objects ||--o{ loans : loaned_item
    users ||--o{ loan_requests : requests
    objects ||--o{ loan_requests : requested_item
    objects ||--o{ consumable_reports : reported_item

    users {
        text user_id PK
        text name
        text email
        text department
        text role
        integer active
    }

    objects {
        text object_id PK
        text name
        text category
        text location
        integer total_quantity
        integer available_quantity
        integer is_consumable
        text image_data
    }

    loans {
        integer loan_id PK
        text user_id FK
        text object_id FK
        integer quantity
        text checkout_time
        text due_time
        text return_time
        text status
    }

    loan_requests {
        integer request_id PK
        text user_id FK
        text object_id FK
        integer quantity
        text lending_date
        text return_date
        text status
    }

    consumable_reports {
        integer report_id PK
        text object_id FK
        integer quantity
        text reported_by
        text status
    }

    events {
        integer event_id PK
        text event_time
        text event_type
        text message
    }

    system_settings {
        text key PK
        text value
        text updated_at
    }

    user_groups {
        integer group_id PK
        text name
        text department
    }
```

## Recommended Learning Route

1. Start at `main.py`.
2. Read `backend/server.py` until you understand how `/api/...` routes are chosen.
3. Pick one workflow, for example checkout.
4. Follow `frontend/js/actions.js` -> `/api/checkout` -> `backend/server.py` -> `backend/services/loans.py`.
5. Check which tables are touched in `backend/database.py`.
6. Repeat with return, object admin, user admin, and notifications.

