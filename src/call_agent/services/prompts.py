from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from call_agent.domain.models import Clinic, Doctor, Route


def build_system_prompt(
    route: Route,
    clinic: Clinic,
    doctor: Doctor | None = None,
) -> str:
    tz = ZoneInfo(clinic.timezone)
    now = datetime.now(tz)
    date_str = now.strftime("%A, %d/%m/%Y")
    time_str = now.strftime("%H:%M")

    parts: list[str] = [
        "אתה עוזר מזכירות רפואית. אתה עוזר למטופלים לקבוע תורים, לענות על שאלות",
        "על המרפאה והרופאים, ולספק מידע על שירותים.",
        "",
        f"מרפאה: {clinic.name}",
        f"כתובת: {clinic.address}",
        f"טלפון: {clinic.phone}",
    ]

    if doctor:
        parts.append("")
        parts.append(f"רופא/ה: ד\"ר {doctor.first_name} {doctor.last_name}")
        parts.append(f"התמחות: {doctor.specialty}")
        parts.append(
            "אתה מסייע רק בנוגע לרופא/ה זה/זו. "
            "אם המטופל שואל על רופא אחר, הפנה אותו למספר המתאים."
        )
    else:
        parts.append("")
        parts.append("אתה מסייע בנוגע לכל הרופאים במרפאה.")

    parts.extend([
        "",
        f"תאריך: {date_str}",
        f"שעה: {time_str}",
        "",
        "כללי התנהגות:",
        "- דבר בעברית תמיד",
        "- היה מנומס ומקצועי",
        "- לפני קביעת תור, וודא את כל הפרטים עם המטופל",
        "- אם חסר מידע, שאל את המטופל",
        "- אל תמציא מידע — השתמש רק בכלים הזמינים",
        "- כשמטופל חדש פונה, חפש אותו לפי מספר טלפון לפני יצירת רשומה חדשה",
    ])

    if route.system_prompt_override:
        parts.extend(["", route.system_prompt_override])

    return "\n".join(parts)
