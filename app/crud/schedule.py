from calendar import weekday
from turtle import update
from typing import List

from app.models.schedule import GroupStatsModel, LessonModel, ScheduleModelResponse, ScheduleModel, ScheduleUpdateModel, TeacherLessonModel, TeacherSchedulesModelResponse
from app.core.config import DATABASE_NAME, SCHEDULE_COLLECTION_NAME, SCHEDULE_GROUPS_STATS, SCHEDULE_UPDATES_COLLECTION
from app.database.database import AsyncIOMotorClient


def save_schedule(
    conn: AsyncIOMotorClient,
    group: str,
    schedule: ScheduleModel
):
    """Сохранение или обновление расписания группы."""
    conn[DATABASE_NAME][SCHEDULE_COLLECTION_NAME].update_one(
        {'group': group},
        {'$set': {'group': group,
                  'schedule':  schedule.dict()}},
        upsert=True
    )


async def get_full_schedule(
    conn: AsyncIOMotorClient,
    group_name: str
) -> ScheduleModelResponse:
    """Получение полного расписания для выбранной группы"""
    schedule = await conn[DATABASE_NAME][SCHEDULE_COLLECTION_NAME].find_one(
        {'group': group_name}, {'_id': 0})

    if schedule:
        schedule_with_num_keys = {
            '1': schedule['schedule']['monday'],
            '2': schedule['schedule']['tuesday'],
            '3': schedule['schedule']['wednesday'],
            '4': schedule['schedule']['thursday'],
            '5': schedule['schedule']['friday'],
            '6': schedule['schedule']['saturday'],
        }
        return ScheduleModelResponse(group=schedule['group'],
                                     schedule=schedule_with_num_keys)


async def get_groups(conn: AsyncIOMotorClient) -> List[str]:
    """Получение списка всех групп, для которых доступно расписание"""
    cursor = conn[DATABASE_NAME][SCHEDULE_COLLECTION_NAME].find(
        {}, {'group': 1, '_id': 0})
    groups = await cursor.to_list(None)
    groups = [group['group'] for group in groups]

    if len(groups) > 0:
        return groups


async def find_teacher(conn: AsyncIOMotorClient, teacher_name: str) -> TeacherSchedulesModelResponse:
    # todo: [А-Яа-я]+\s+[А-Яа-я]\.\s*[А-Я]\.
    request_data = {'$or': [
        {"schedule.monday.lessons": {'$elemMatch': {
            '$elemMatch': {"teachers": {'$regex': teacher_name, '$options': 'i'}}}}},
        {"schedule.tuesday.lessons": {'$elemMatch': {
            '$elemMatch': {"teachers": {'$regex': teacher_name, '$options': 'i'}}}}},
        {"schedule.wednesday.lessons": {'$elemMatch': {
            '$elemMatch': {"teachers": {'$regex': teacher_name, '$options': 'i'}}}}},
        {"schedule.thursday.lessons": {'$elemMatch': {
            '$elemMatch': {"teachers": {'$regex': teacher_name, '$options': 'i'}}}}},
        {"schedule.friday.lessons": {'$elemMatch': {
            '$elemMatch': {"teachers": {'$regex': teacher_name, '$options': 'i'}}}}},
        {"schedule.saturday.lessons": {'$elemMatch': {
            '$elemMatch': {"teachers": {'$regex': teacher_name, '$options': 'i'}}}}},
    ]}

    cursor = conn[DATABASE_NAME][SCHEDULE_COLLECTION_NAME].find(request_data, {
                                                                '_id': 0})
    schedules = await cursor.to_list(None)

    result = []

    for schedule in schedules:
        schedule_with_num_keys = {
            '1': schedule['schedule']['monday'],
            '2': schedule['schedule']['tuesday'],
            '3': schedule['schedule']['wednesday'],
            '4': schedule['schedule']['thursday'],
            '5': schedule['schedule']['friday'],
            '6': schedule['schedule']['saturday'],
        }

        for i in range(1, 7):
            lessons_in_day = schedule_with_num_keys[str(i)]['lessons']
            for lesson_num in range(len(lessons_in_day)):
                for lesson in lessons_in_day[lesson_num]:
                    for teacher in lesson['teachers']:
                        if teacher.lower().find(teacher_name.lower()) != -1:
                            teacher_lesson = TeacherLessonModel(
                                group=schedule['group'], weekday=i,
                                lesson_number=lesson_num, lesson=LessonModel(**lesson))
                            result.append(teacher_lesson)

    teacher_schedule = TeacherSchedulesModelResponse(schedules=result)

    if len(result) > 0:
        return teacher_schedule


async def update_schedule_updates(conn: AsyncIOMotorClient, updates: List[ScheduleUpdateModel]):
    for update in updates:
        groups_list = []
        request_to_db = {'$or': groups_list}
        for group in update.groups:
            groups_list.append({"groups": {'$elemMatch': {'$regex': group}}})

        update_in_db = await conn[DATABASE_NAME][SCHEDULE_UPDATES_COLLECTION].find_one(request_to_db)

        if update_in_db:
            await conn[DATABASE_NAME][SCHEDULE_UPDATES_COLLECTION].update_one({'_id': update_in_db['_id']}, {"$set": update.dict()})
        else:
            await conn[DATABASE_NAME][SCHEDULE_UPDATES_COLLECTION].insert_one(update.dict())


async def get_all_schedule_updates(conn: AsyncIOMotorClient) -> List[ScheduleUpdateModel]:
    cursor = conn[DATABASE_NAME][SCHEDULE_UPDATES_COLLECTION].find(
        {}, {'_id': 0})

    updates = await cursor.to_list(None)
    updates = [ScheduleUpdateModel(**update) for update in updates]

    if len(updates) > 0:
        return updates


async def get_schedule_update_by_group(conn: AsyncIOMotorClient, group: str) -> ScheduleUpdateModel:
    update = await conn[DATABASE_NAME][SCHEDULE_UPDATES_COLLECTION].find_one(
        {"groups": {'$elemMatch': {'$regex': group}}}, {'_id': 0})

    if update:
        return ScheduleUpdateModel(**update)


async def update_group_stats(conn: AsyncIOMotorClient, group: str):
    update = await conn[DATABASE_NAME][SCHEDULE_GROUPS_STATS].update_one(
        {"group": group},  {'$inc': {'received': 1}}, upsert=True)


async def get_groups_stats(conn: AsyncIOMotorClient) -> List[GroupStatsModel]:
    cursor = conn[DATABASE_NAME][SCHEDULE_GROUPS_STATS].find(
        {}, {'_id': 0})

    groups_stats = await cursor.to_list(None)
    groups_stats = [GroupStatsModel(**stats) for stats in groups_stats]

    if len(groups_stats) > 0:
        return groups_stats
