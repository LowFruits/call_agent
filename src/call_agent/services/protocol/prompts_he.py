from __future__ import annotations

# All Hebrew strings used by the protocol. Centralised so the flow logic stays
# language-neutral and copy can be tweaked without touching handlers.

GREETING_AND_INTENT_MENU = (
    "שלום! אני המזכירה הדיגיטלית. במה אפשר לעזור?\n"
    "1. בקשר לתור קיים\n"
    "2. לקבוע תור חדש\n"
    "3. להשאיר הודעה למזכירה"
)

INTENT_NOT_UNDERSTOOD = (
    "לא הבנתי. אנא בחר אחת מהאפשרויות:\n"
    "1. בקשר לתור קיים\n"
    "2. לקבוע תור חדש\n"
    "3. להשאיר הודעה למזכירה"
)

# --- New booking ---

ASK_FIRST_VISIT = (
    "האם זה הביקור הראשון שלך אצל הרופא?\n"
    "1. כן\n"
    "2. לא"
)

ASK_KUPAT_CHOLIM = (
    "מאיזה קופת חולים אתה?\n"
    "1. כללית\n"
    "2. מכבי\n"
    "3. מאוחדת\n"
    "4. לאומית\n"
    "5. פרטי"
)

CONFIRM_PRIVATE = (
    "במסלול פרטי יש עלות נוספת על התור.\n"
    "האם להמשיך עם תור פרטי?\n"
    "1. כן\n"
    "2. לא"
)

ASK_BIRTH_DATE = "מה תאריך הלידה שלך? (פורמט: יום/חודש/שנה)"
INVALID_DATE = "תאריך לא תקין. אנא הקלד בפורמט יום/חודש/שנה (לדוגמה 15/06/1985)."

ASK_VISIT_TYPE = (
    "איזה סוג ביקור תרצה?\n"
    "1. טלפוני\n"
    "2. פרונטלי (במרפאה)"
)

ASK_FOR_SELF = (
    "האם התור עבורך?\n"
    "1. כן\n"
    "2. לא"
)
ASK_OTHER_NAME = "מה שם המטופל עבורו התור?"
ASK_OTHER_ID = "מה תעודת הזהות של המטופל? (9 ספרות)"
ASK_OTHER_RELATION = "מה הקרבה שלך אליו? (למשל: בן, אמא, בן/בת זוג)"

ASK_PATIENT_ID = "מה התעודת הזהות שלך? (9 ספרות)"
INVALID_ID = "תעודת זהות לא תקינה. אנא הקלד 9 ספרות תקינות."

ASK_NAME = "מה השם המלא שלך?"

ASK_SMS_CONSENT = (
    "האם תרצה לקבל הודעת אישור עם פרטי התור?\n"
    "(שירות זה כרוך בעלות נוספת)\n"
    "1. כן\n"
    "2. לא"
)

# --- Time selection sub-FSM ---

ASK_TIME_MODE = (
    "איך תרצה לבחור מועד לתור?\n"
    "1. התורים הקרובים ביותר\n"
    "2. תאריך מסוים"
)

WORKING_DAYS_TEMPLATE = (
    "הרופא מקבל בימי: {days}.\n"
    "מה התאריך שתרצה? (יום/חודש/שנה)"
)

ASK_SPECIFIC_DATE = "מה התאריך שתרצה? (יום/חודש/שנה)"

DATE_NOT_WORKING_DAY = (
    "הרופא לא מקבל בתאריך זה.\n"
    "אנא בחר תאריך אחר (יום/חודש/שנה)."
)

# Closest-slot offer. {listing} renders the numbered slot list grouped by window.
OFFER_CLOSEST_TEMPLATE = (
    "להלן התורים הזמינים הקרובים ביותר:\n\n"
    "{listing}\n\n"
    "בחר מספר, או כתוב 'לא' לאפשרויות נוספות."
)

# Specific-date offer — 3 slots spread across the day.
OFFER_DATE_SLOTS_TEMPLATE = (
    "תורים זמינים בתאריך {date_str}:\n\n"
    "{listing}\n\n"
    "בחר מספר, או כתוב 'לא' לאפשרויות נוספות."
)

NO_MORE_DATE_SLOTS = (
    "אין עוד תורים זמינים בתאריך זה.\n"
    "אנא בחר תאריך אחר (יום/חודש/שנה)."
)

# Fallback when literally no slots exist for the next half year.
NO_SLOTS_HALF_YEAR_OFFER_MESSAGE = (
    "אין תורים פנויים בששת החודשים הקרובים.\n"
    "האם תרצה להשאיר הודעה למזכירה?\n"
    "1. כן\n"
    "2. לא"
)

BOOKING_SLOT_GONE = "התור הזה אינו זמין יותר. ננסה למצוא תור אחר."

# Window-bucket headers used by the closest listing.
WINDOW_LABEL_MORNING = "בוקר"
WINDOW_LABEL_NOON = "צהריים"
WINDOW_LABEL_EVENING = "ערב"

# --- Existing appointment ---

NO_EXISTING_APPT = "לא מצאתי תור פעיל על שמך. רוצה לקבוע תור חדש?"

EXISTING_ACTION_MENU_TEMPLATE = (
    "התור הקיים שלך:\n"
    "{summary}\n\n"
    "מה תרצה לעשות?\n"
    "1. לקבל פרטים נוספים\n"
    "2. לשנות את התור\n"
    "3. לבטל את התור"
)

ASK_MORE_INFO_QUESTION = (
    "מה תרצה לדעת על התור? נציג אנושי יחזור אליך עם המידע."
)

CONFIRM_CANCEL = (
    "האם אתה בטוח שברצונך לבטל את התור?\n"
    "1. כן\n"
    "2. לא"
)
CANCELLED_CONFIRMATION = "התור בוטל בהצלחה. בריאות טובה!"
CANCEL_ABORTED = "ביטול הופסק. התור נשאר במערכת."

RESCHEDULE_OFFER_MENU_TEMPLATE = (
    "התור החדש המוצע: {when}.\n"
    "1. אשר\n"
    "2. תור אחר\n"
    "3. שנה משהו אחר"
)

RESCHEDULE_CHANGE_MENU = (
    "מה תרצה לשנות?\n"
    "1. סוג ביקור\n"
    "2. קופת חולים"
)

# --- Leave message ---

ASK_MESSAGE_BODY = "כתוב את ההודעה ונציג יחזור אליך בהקדם."
MESSAGE_SAVED = "תודה! ההודעה נשמרה ונציג יחזור אליך בהקדם."

# --- Summaries / terminals ---

SUMMARY_CONFIRM_NEW_TEMPLATE = (
    "סיכום התור החדש:\n"
    "{summary}\n\n"
    "לאשר ולקבוע?\n"
    "1. כן\n"
    "2. לא"
)

SUMMARY_CONFIRM_RESCHEDULE_TEMPLATE = (
    "סיכום השינוי:\n"
    "{summary}\n\n"
    "לאשר את השינוי?\n"
    "1. כן\n"
    "2. לא"
)

BOOKING_DONE = "התור נקבע בהצלחה!"
BOOKING_FAILED = "מצטערים, לא הצלחנו לקבוע את התור כרגע. אנא נסה שוב מאוחר יותר."
RESCHEDULE_DONE = "התור עודכן בהצלחה!"
GENERIC_GOODBYE = "תודה! יום נעים."
GENERIC_NOT_UNDERSTOOD = "לא הבנתי. אנא נסה שוב."
