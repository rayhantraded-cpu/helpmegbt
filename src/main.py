import datetime
import os
import random
import webbrowser
from pathlib import Path

import flet as ft

from database import export_database, get_storage_path, init_db, get_state, set_state
from db_operations import (
    add_task,
    count_period_tasks,
    delete_task,
    get_categories,
    get_stats,
    get_tasks_for_period,
    import_legacy_json,
    set_task_completion,
    update_stats_after_completion,
)

APP_NAME = "المساعد الشخصي والإنجاز"
VERSION = "2.0.0"

PERIODS = [
    ("يومية", "DAILY", ft.Icons.TODAY),
    ("أسبوعية", "WEEKLY", ft.Icons.DATE_RANGE),
    ("شهرية", "MONTHLY", ft.Icons.CALENDAR_MONTH),
]

CATEGORY_EMOJI = {
    "مهام روحية": "🕊️",
    "مهام بدنية وصحية": "💪",
    "مهام تطويرية": "🚀",
    "مهام تعليمية": "📚",
    "مهام اجتماعية": "🤝",
    "مهام اقتصادية": "💰",
}

CATEGORY_TIPS = {
    "مهام روحية": ["الورد اليومي للقرآن الكريم.", "أذكار الصباح والمساء.", "المحافظة على السنن الرواتب."],
    "مهام بدنية وصحية": ["المشي 10 دقائق.", "تمارين الضغط والقرفصاء.", "شرب كمية كافية من الماء."],
    "مهام تطويرية": ["تعلم ميزة جديدة.", "التدرب على Python أو قواعد البيانات.", "تحسين مهارة عملية."],
    "مهام تعليمية": ["قراءة 10 صفحات.", "التدرب على اللغة الإنجليزية.", "مراجعة درس متخصص."],
    "مهام اجتماعية": ["صلة الرحم.", "جلسة عائلية بلا شاشات.", "تفقد أحوال من تحب."],
    "مهام اقتصادية": ["مراجعة المصروفات.", "تخصيص مبلغ للادخار.", "البحث عن فكرة لتحسين الإيرادات."],
}

MOTIVATION = [
    "✨ الاستمرارية أهم من الكمال.",
    "🚀 مهمة صغيرة اليوم تصنع نتيجة كبيرة غدًا.",
    "🔥 لا تنتظر الحماس؛ ابدأ وسيأتي الحماس.",
    "🌱 ابنِ عادة واحدة قوية بدل عشر عادات ضعيفة.",
]


def main(page: ft.Page):
    page.title = APP_NAME
    page.rtl = True
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK if get_state("theme_mode", "light") == "dark" else ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.GREY_50

    init_db()

    # Import the previous JSON database, if it exists in the app storage.
    legacy_path = get_storage_path() / "tasks_data.json"
    import_legacy_json(legacy_path)

    categories = get_categories()
    stats = get_stats()
    state = {
        "period": "يومية",
        "category": "",
    }

    # ---------- helpers ----------

    def freq_for_period(name):
        return dict((p[0], p[1]) for p in PERIODS).get(name, "DAILY")

    def notify(message):
        page.show_dialog(ft.SnackBar(content=ft.Text(message, text_align=ft.TextAlign.RIGHT)))

    def refresh():
        render_tasks()
        render_header()
        page.update()

    # ---------- header ----------

    streak_value = ft.Text(str(stats["streak"]), size=18, weight=ft.FontWeight.BOLD)
    points_value = ft.Text(str(stats["points"]), size=18, weight=ft.FontWeight.BOLD)

    def render_header():
        fresh = get_stats()
        stats.update(fresh)
        streak_value.value = str(stats["streak"])
        points_value.value = str(stats["points"])

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=16, vertical=14),
        bgcolor=ft.Colors.BLUE_700,
        content=ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.MENU,
                    icon_color=ft.Colors.WHITE,
                    tooltip="القائمة",
                    on_click=lambda e: page.show_drawer(drawer),
                ),
                ft.Column(
                    [
                        ft.Text(APP_NAME, color=ft.Colors.WHITE, size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(VERSION, color=ft.Colors.WHITE70, size=11),
                    ],
                    spacing=0,
                    expand=True,
                ),
                ft.Container(
                    padding=8,
                    border_radius=14,
                    bgcolor=ft.Colors.WHITE24,
                    content=ft.Row(
                        [ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color=ft.Colors.ORANGE_200, size=18), streak_value],
                        spacing=4,
                    ),
                ),
                ft.Container(
                    padding=8,
                    border_radius=14,
                    bgcolor=ft.Colors.WHITE24,
                    content=ft.Row(
                        [ft.Icon(ft.Icons.STARS, color=ft.Colors.AMBER_200, size=18), points_value],
                        spacing=4,
                    ),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    # ---------- filters ----------

    category_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)

    def select_category(name):
        state["category"] = "" if state["category"] == name else name
        render_filters()
        render_tasks()
        page.update()

    def render_filters():
        category_row.controls.clear()
        category_row.controls.append(
            ft.FilterChip(
                label=ft.Text("الكل"),
                selected=state["category"] == "",
                on_select=lambda e: select_category(""),
            )
        )
        for c in categories:
            name = c["name"]
            category_row.controls.append(
                ft.FilterChip(
                    label=ft.Text(f"{CATEGORY_EMOJI.get(name, '📌')} {name.replace('مهام ', '')}"),
                    selected=state["category"] == name,
                    on_select=lambda e, n=name: select_category(n),
                )
            )

    period_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        tabs=[ft.Tab(text=x[0], icon=x[2]) for x in PERIODS],
    )

    def period_changed(e):
        state["period"] = PERIODS[period_tabs.selected_index][0]
        state["category"] = ""
        render_filters()
        render_tasks()
        page.update()

    period_tabs.on_change = period_changed

    # ---------- task list ----------

    task_list = ft.ListView(expand=True, spacing=10, padding=ft.padding.only(bottom=90))

    def task_card(task):
        done = bool(task["is_completed"])
        category = task["category_name"]
        color = task["color_code"]
        title = task["title"]
        target = int(task["target_count"] or 1)

        def changed(e):
            value = bool(e.control.value)
            set_task_completion(task["id"], value, task["frequency_type"])
            update_stats_after_completion(value)
            notify("🎉 ممتاز! +10 نقاط" if value else "↩️ تم التراجع عن الإنجاز.")
            render_tasks()
            render_header()
            page.update()

        def open_link(e):
            url = (task.get("resource_url") or "").strip()
            if not url:
                return
            try:
                webbrowser.open(url)
            except Exception:
                notify("تعذر فتح الرابط على هذا الجهاز.")

        def remove(e):
            def confirm_delete(ev):
                delete_task(task["id"])
                page.close(confirm)
                notify("تم حذف المهمة.")
                render_tasks()
                page.update()

            confirm = ft.AlertDialog(
                modal=True,
                title=ft.Text("حذف المهمة"),
                content=ft.Text("هل تريد حذف هذه المهمة نهائيًا؟"),
                actions=[
                    ft.TextButton("إلغاء", on_click=lambda ev: page.close(confirm)),
                    ft.FilledButton("حذف", on_click=confirm_delete),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(confirm)

        actions = [
            ft.Checkbox(value=done, on_change=changed),
        ]
        if task.get("resource_url"):
            actions.append(ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, tooltip="فتح الرابط", on_click=open_link))
        actions.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="حذف", on_click=remove))

        return ft.Container(
            padding=14,
            border_radius=18,
            bgcolor=ft.Colors.WHITE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_900,
            border=ft.border.all(1, color=ft.Colors.GREY_200 if not done else color),
            content=ft.Row(
                [
                    ft.Container(
                        width=6,
                        height=62,
                        border_radius=6,
                        bgcolor=color,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                title,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_500 if done else None,
                                decoration=ft.TextDecoration.LINE_THROUGH if done else None,
                            ),
                            ft.Row(
                                [
                                    ft.Text(f"{CATEGORY_EMOJI.get(category, '📌')} {category.replace('مهام ', '')}", size=11, color=color),
                                    ft.Text(f"• الهدف: {target}", size=11, color=ft.Colors.GREY_600),
                                ],
                                spacing=6,
                            ),
                            ft.Text(task.get("advice_text") or "", size=11, color=ft.Colors.GREY_600, max_lines=2),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Row(actions, spacing=0),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def render_tasks():
        task_list.controls.clear()
        tasks = get_tasks_for_period(freq_for_period(state["period"]), state["category"])
        if not tasks:
            task_list.controls.append(
                ft.Container(
                    padding=40,
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=54, color=ft.Colors.GREY_400),
                            ft.Text("لا توجد مهام هنا بعد.", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text("أضف أول مهمة وابدأ التقدم.", color=ft.Colors.GREY_600),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        else:
            for task in tasks:
                task_list.controls.append(task_card(task))

    # ---------- add task dialog ----------

    title_input = ft.TextField(label="اسم المهمة", autofocus=True, rtl=True)
    link_input = ft.TextField(label="رابط اختياري", rtl=True, keyboard_type=ft.KeyboardType.URL)
    count_input = ft.TextField(label="الهدف / العدد", value="1", keyboard_type=ft.KeyboardType.NUMBER, rtl=True)
    advice_input = ft.TextField(label="ملاحظة أو نصيحة", multiline=True, min_lines=2, max_lines=4, rtl=True)
    category_dropdown = ft.Dropdown(
        label="التصنيف",
        options=[ft.DropdownOption(key=c["name"], text=f"{CATEGORY_EMOJI.get(c['name'], '📌')} {c['name']}") for c in categories],
        value=categories[0]["name"] if categories else None,
    )
    period_dropdown = ft.Dropdown(
        label="التكرار",
        options=[ft.DropdownOption(key=x[0], text=x[0]) for x in PERIODS],
        value="يومية",
    )

    def save_new_task(e):
        title = (title_input.value or "").strip()
        if not title:
            notify("اكتب اسم المهمة أولًا.")
            return
        try:
            count = max(1, int((count_input.value or "1").strip()))
        except ValueError:
            notify("العدد يجب أن يكون رقمًا صحيحًا.")
            return

        add_task(
            title=title,
            category_name=category_dropdown.value or categories[0]["name"],
            frequency_type=period_dropdown.value or "يومية",
            target_count=count,
            resource_url=(link_input.value or "").strip(),
            advice_text=(advice_input.value or "").strip(),
        )
        title_input.value = ""
        link_input.value = ""
        count_input.value = "1"
        advice_input.value = ""
        page.close(add_dialog)
        notify("تمت إضافة المهمة بنجاح.")
        render_tasks()
        page.update()

    add_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("إضافة مهمة جديدة"),
        content=ft.Column(
            [title_input, category_dropdown, period_dropdown, count_input, link_input, advice_input],
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        actions=[
            ft.TextButton("إلغاء", on_click=lambda e: page.close(add_dialog)),
            ft.FilledButton("إضافة", icon=ft.Icons.ADD_TASK, on_click=save_new_task),
        ],
    )

    # ---------- reports ----------

    report_text = ft.Text()

    def open_reports(e):
        lines = []
        total_all = 0
        completed_all = 0
        for label, freq, _ in PERIODS:
            total, completed = count_period_tasks(freq)
            total_all += total
            completed_all += completed
            ratio = round((completed / total) * 100) if total else 0
            lines.append(f"{label}: {completed} / {total}  ({ratio}%)")
        overall = round((completed_all / total_all) * 100) if total_all else 0
        report_text.value = "\n".join(lines) + f"\n\nالإجمالي: {completed_all} / {total_all}  ({overall}%)"
        report_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("📊 تقرير الإنجاز"),
            content=ft.Container(
                width=420,
                padding=10,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.INSIGHTS, size=48, color=ft.Colors.BLUE_600),
                        report_text,
                        ft.Divider(),
                        ft.Text(f"النقاط: {get_stats()['points']}", weight=ft.FontWeight.BOLD),
                        ft.Text(f"السلسلة: {get_stats()['streak']} أيام", weight=ft.FontWeight.BOLD),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
            ),
            actions=[ft.FilledButton("إغلاق", on_click=lambda ev: page.close(report_dialog))],
        )
        page.show_dialog(report_dialog)

    # ---------- settings ----------

    def toggle_theme(e):
        dark = page.theme_mode == ft.ThemeMode.LIGHT
        page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT
        set_state("theme_mode", "dark" if dark else "light")
        page.bgcolor = ft.Colors.GREY_950 if dark else ft.Colors.GREY_50
        page.close(settings_dialog)
        notify("تم تحديث المظهر.")
        page.update()

    def create_backup(e):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target = get_storage_path() / f"backup_{stamp}.db"
        export_database(str(target))
        page.close(settings_dialog)
        notify(f"تم إنشاء نسخة احتياطية داخل بيانات التطبيق: {target.name}")

    settings_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("⚙️ الإعدادات"),
        content=ft.Column(
            [
                ft.Text(f"الإصدار {VERSION}"),
                ft.Text("قاعدة البيانات: SQLite محلية ومهيأة للعمل على Android."),
                ft.Divider(),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DARK_MODE),
                    title=ft.Text("الوضع الداكن / الفاتح"),
                    trailing=ft.IconButton(icon=ft.Icons.SWITCH_LEFT, on_click=toggle_theme),
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.BACKUP),
                    title=ft.Text("إنشاء نسخة احتياطية"),
                    on_click=create_backup,
                ),
                ft.Text("ملاحظة: قبل النشر التجاري، أضف نظام ترخيص حقيقي بدل أي مفتاح ثابت داخل التطبيق.", size=12, color=ft.Colors.ORANGE_800),
            ],
            tight=True,
        ),
        actions=[ft.TextButton("إغلاق", on_click=lambda e: page.close(settings_dialog))],
    )

    # ---------- drawer ----------

    drawer_content = ft.Column(expand=True, spacing=8)
    drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Text("🏆 إنجازاتك", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text("نظرة سريعة على تقدمك", color=ft.Colors.GREY_600),
                        ft.Divider(),
                        drawer_content,
                    ],
                    expand=True,
                ),
            )
        ]
    )

    def update_drawer():
        drawer_content.controls.clear()
        for label, freq, _ in PERIODS:
            total, completed = count_period_tasks(freq)
            drawer_content.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE if total and completed == total else ft.Icons.RADIO_BUTTON_UNCHECKED),
                    title=ft.Text(label),
                    subtitle=ft.Text(f"{completed} من {total} مكتملة"),
                )
            )
        drawer_content.controls.extend(
            [
                ft.Divider(),
                ft.ListTile(leading=ft.Icon(ft.Icons.INSIGHTS), title=ft.Text("التقارير"), on_click=lambda e: (page.close_drawer(), open_reports(e))),
                ft.ListTile(leading=ft.Icon(ft.Icons.SETTINGS), title=ft.Text("الإعدادات"), on_click=lambda e: (page.close_drawer(), page.show_dialog(settings_dialog))),
            ]
        )

    drawer.on_dismiss = lambda e: None
    original_show_drawer = header.content.controls[0].on_click

    # Rebind menu so the drawer is refreshed first.
    header.content.controls[0].on_click = lambda e: (update_drawer(), page.show_drawer(drawer))

    # ---------- main layout ----------

    render_filters()
    render_tasks()

    add_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        tooltip="إضافة مهمة",
        on_click=lambda e: page.show_dialog(add_dialog),
    )

    body = ft.Column(
        [
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                content=ft.Column(
                    [
                        ft.Text(random.choice(MOTIVATION), size=13, color=ft.Colors.BLUE_800, weight=ft.FontWeight.BOLD),
                        period_tabs,
                        category_row,
                    ],
                    spacing=10,
                ),
            ),
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=12),
                content=task_list,
            ),
        ],
        expand=True,
        spacing=0,
    )

    page.add(
        ft.Column(
            [
                header,
                body,
            ],
            expand=True,
            spacing=0,
        )
    )
    page.overlay.append(add_button)
    page.update()


if __name__ == "__main__":
    ft.run(main)
