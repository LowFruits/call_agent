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

ASK_FIRST_VISIT = "האם זה הביקור הראשון שלך אצל הרופא? (כן/לא)"

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
    "האם להמשיך עם תור פרטי? (כן/לא)"
)

ASK_BIRTH_DATE = "מה תאריך הלידה שלך? (פורמט: יום/חודש/שנה)"
INVALID_DATE = "תאריך לא תקין. אנא הקלד בפורמט יום/חודש/שנה (לדוגמה 15/06/1985)."

ASK_VISIT_TYPE = (
    "איזה סוג ביקור תרצה?\n"
    "1. טלפוני\n"
    "2. פרונטלי (במרפאה)"
)

ASK_FOR_SELF = "האם התור עבורך? (כן/לא)"
ASK_OTHER_NAME = "מה שם המטופל עבורו התור?"
ASK_OTHER_ID = "מה תעודת הזהות של המטופל? (9 ספרות)"
ASK_OTHER_RELATION = "מה הקרבה שלך אליו? (למשל: בן, אמא, בן/בת זוג)"

ASK_PATIENT_ID = "מה התעודת הזהות שלך? (9 ספרות)"
INVALID_ID = "תעודת זהות לא תקינה. אנא הקלד 9 ספרות תקינות."

ASK_NAME = "מה השם המלא שלך?"

ASK_SMS_CONSENT = (
    "האם תרצה לקבל הודעת אישור עם פרטי התור? (כן/לא)\n"
    "(שירות זה כרוך בעלות נוספת)"
)

# --- Time selection sub-FSM ---

ASK_TIME_WINDOW = (
    "באיזה שעות תרצה תור?\n"
    "1. בוקר עד צהריים\n"
    "2. אחר הצהריים עד ערב"
)

ASK_WHEN = (
    "למתי תרצה לקבוע?\n"
    "1. הקרוב ביותר\n"
    "2. במהלך השבוע הקרוב\n"
    "3. תאריך ספציפי"
)

ASK_SPECIFIC_DATE = "מה התאריך שתרצה? (יום/חודש/שנה)"
NO_SLOTS_AVAILABLE = "מצטערים, לא נמצאו תורים זמינים בטווח שביקשת. ננסה טווח אחר?"
BOOKING_SLOT_GONE = "התור הזה אינו זמין יותר. ננסה למצוא תור אחר."
OFFER_SLOT_TEMPLATE = "מצאתי תור פנוי: {when}.\nמאשר? (כן/לא)"

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

CONFIRM_CANCEL = "האם אתה בטוח שברצונך לבטל את התור? (כן/לא)"
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
    "לאשר ולקבוע? (כן/לא)"
)

SUMMARY_CONFIRM_RESCHEDULE_TEMPLATE = (
    "סיכום השינוי:\n"
    "{summary}\n\n"
    "לאשר את השינוי? (כן/לא)"
)

BOOKING_DONE = "התור נקבע בהצלחה!"
BOOKING_FAILED = "מצטערים, לא הצלחנו לקבוע את התור כרגע. אנא נסה שוב מאוחר יותר."
RESCHEDULE_DONE = "התור עודכן בהצלחה!"
GENERIC_GOODBYE = "תודה! יום נעים."
GENERIC_NOT_UNDERSTOOD = "לא הבנתי. אנא נסה שוב."
