
DROP TABLE IF EXISTS admission_applications CASCADE;
DROP TABLE IF EXISTS schedule CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS teacher_disciplines CASCADE;
DROP TABLE IF EXISTS disciplines CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS deans CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS groups_ CASCADE;
DROP TABLE IF EXISTS directions CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS faculties CASCADE;

-- Факультеты
CREATE TABLE faculties (
    faculty_id   SERIAL PRIMARY KEY,
    name         TEXT NOT NULL
);

-- Кафедры
CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,
    faculty_id    INT REFERENCES faculties(faculty_id),
    name          TEXT NOT NULL
);

-- Направления подготовки 
CREATE TABLE directions (
    direction_id   SERIAL PRIMARY KEY,
    faculty_id     INT REFERENCES faculties(faculty_id),
    name           TEXT NOT NULL,
    budget_places  INT NOT NULL,
    paid_places    INT NOT NULL
);

-- Учебные группы
CREATE TABLE groups_ (
    group_id       SERIAL PRIMARY KEY,
    direction_id   INT REFERENCES directions(direction_id),
    name           TEXT NOT NULL,          -- напр. "ИТ-21-1"
    admission_year INT NOT NULL
);

-- Студенты 
CREATE TABLE students (
    student_id     SERIAL PRIMARY KEY,
    full_name      TEXT NOT NULL,
    group_id       INT REFERENCES groups_(group_id),
    admission_year INT NOT NULL
);

-- Преподаватели 
CREATE TABLE teachers (
    teacher_id    SERIAL PRIMARY KEY,
    full_name     TEXT NOT NULL,
    department_id INT REFERENCES departments(department_id),
    position      TEXT NOT NULL            
);

-- Деканы 
CREATE TABLE deans (
    dean_id    SERIAL PRIMARY KEY,
    full_name  TEXT NOT NULL,
    faculty_id INT REFERENCES faculties(faculty_id)
);

-- Прочие сотрудники и администрация 
CREATE TABLE staff (
    staff_id      SERIAL PRIMARY KEY,
    full_name     TEXT NOT NULL,
    position      TEXT NOT NULL,
    department_id INT REFERENCES departments(department_id)
);

-- Дисциплины
CREATE TABLE disciplines (
    discipline_id SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    department_id INT REFERENCES departments(department_id),
    semester      INT NOT NULL
);

-- Кто какую дисциплину ведёт у какой группы
CREATE TABLE teacher_disciplines (
    id             SERIAL PRIMARY KEY,
    teacher_id     INT REFERENCES teachers(teacher_id),
    discipline_id  INT REFERENCES disciplines(discipline_id),
    group_id       INT REFERENCES groups_(group_id),
    semester       INT NOT NULL
);

-- Оценки студентов 
CREATE TABLE grades (
    grade_id      SERIAL PRIMARY KEY,
    student_id    INT REFERENCES students(student_id),
    discipline_id INT REFERENCES disciplines(discipline_id),
    semester      INT NOT NULL,
    grade         INT,                 -- 2..5, NULL если не сдавал
    has_debt      BOOLEAN NOT NULL DEFAULT FALSE
);

-- Аудитории
CREATE TABLE rooms (
    room_id  SERIAL PRIMARY KEY,
    name     TEXT NOT NULL,
    building TEXT NOT NULL,
    capacity INT NOT NULL
);

-- Расписание
CREATE TABLE schedule (
    schedule_id   SERIAL PRIMARY KEY,
    group_id      INT REFERENCES groups_(group_id),
    discipline_id INT REFERENCES disciplines(discipline_id),
    teacher_id    INT REFERENCES teachers(teacher_id),
    room_id       INT REFERENCES rooms(room_id),
    day_of_week   INT NOT NULL,        -- 1=Пн ... 6=Сб
    start_time    TIME NOT NULL,
    end_time      TIME NOT NULL
);

-- Приёмная кампания 
CREATE TABLE admission_applications (
    application_id SERIAL PRIMARY KEY,
    applicant_name TEXT NOT NULL,
    direction_id   INT REFERENCES directions(direction_id),
    year           INT NOT NULL,
    ege_score      INT NOT NULL,
    status         TEXT NOT NULL       
);

-- Индексы под типичные запросы ассистента
CREATE INDEX idx_students_group ON students(group_id);
CREATE INDEX idx_grades_student ON grades(student_id);
CREATE INDEX idx_grades_discipline ON grades(discipline_id);
CREATE INDEX idx_admission_direction_year ON admission_applications(direction_id, year);
CREATE INDEX idx_schedule_group ON schedule(group_id);
