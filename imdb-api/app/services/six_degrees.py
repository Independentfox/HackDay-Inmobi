"""
Six Degrees of Separation — BFS through person→movie→person connections.
Given person_a_id and person_b_id, find the shortest connection chain.
"""

from collections import deque
from sqlalchemy.orm import Session
from sqlalchemy import text

MAX_DEGREES = 6


def find_connection(db: Session, person_a_id: int, person_b_id: int) -> dict:
    if person_a_id == person_b_id:
        result = db.execute(text("SELECT name FROM people WHERE id = :id"), {"id": person_a_id}).fetchone()
        name = result[0] if result else "Unknown"
        return {
            "found": True,
            "degrees": 0,
            "path": [{"person_id": person_a_id, "person_name": name, "connected_via_movie_id": None, "connected_via_movie_title": None}]
        }

    visited_people = {person_a_id}

    start_result = db.execute(text("SELECT name FROM people WHERE id = :id"), {"id": person_a_id}).fetchone()
    if not start_result:
        return {"found": False, "degrees": -1, "path": []}
    start_name = start_result[0]

    target_result = db.execute(text("SELECT name FROM people WHERE id = :id"), {"id": person_b_id}).fetchone()
    if not target_result:
        return {"found": False, "degrees": -1, "path": []}

    queue = deque()
    initial_path = [{"person_id": person_a_id, "person_name": start_name, "connected_via_movie_id": None, "connected_via_movie_title": None}]
    queue.append((person_a_id, initial_path))

    while queue:
        current_person_id, current_path = queue.popleft()
        current_degrees = len(current_path) - 1

        if current_degrees >= MAX_DEGREES:
            continue

        movies = db.execute(
            text("SELECT DISTINCT c.movie_id, m.title FROM credits c JOIN movies m ON c.movie_id = m.id WHERE c.person_id = :pid"),
            {"pid": current_person_id}
        ).fetchall()

        for movie_id, movie_title in movies:
            coworkers = db.execute(
                text("SELECT DISTINCT c.person_id, p.name FROM credits c JOIN people p ON c.person_id = p.id WHERE c.movie_id = :mid AND c.person_id != :pid"),
                {"mid": movie_id, "pid": current_person_id}
            ).fetchall()

            for coworker_id, coworker_name in coworkers:
                if coworker_id in visited_people:
                    continue

                new_path = current_path + [{
                    "person_id": coworker_id,
                    "person_name": coworker_name,
                    "connected_via_movie_id": movie_id,
                    "connected_via_movie_title": movie_title
                }]

                if coworker_id == person_b_id:
                    return {
                        "found": True,
                        "degrees": len(new_path) - 1,
                        "path": new_path
                    }

                visited_people.add(coworker_id)
                queue.append((coworker_id, new_path))

    return {"found": False, "degrees": -1, "path": []}
