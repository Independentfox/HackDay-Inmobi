"""
Seed script — populates the database with sample movies, people, credits,
users, ratings, and reviews for demo/judging purposes.
"""
import os
import sys
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal, Base
from app.models import Movie, Person, Credit, User, Rating, Review
from app.models.watchlist import WatchlistItem


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            print("Database already seeded. Skipping.")
            return

        # --- Users ---
        usernames = [
            "alice", "bob", "charlie", "diana", "eve",
            "frank", "grace", "heidi", "ivan", "judy",
            "karl", "lara", "mike", "nina", "oscar",
            "priya", "quinn", "ravi", "sara", "tom"
        ]
        users = []
        for username in usernames:
            u = User(username=username)
            db.add(u)
            users.append(u)
        db.flush()

        # --- People ---
        # idx: Name (birth_year)
        people_data = [
            # 0
            ("Shah Rukh Khan", 1965, "Indian actor known as the King of Bollywood, with over 80 films.", "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Shah_Rukh_Khan_graces_the_launch_of_new_Tag_Heuer_watch_collection_%28cropped%29.jpg/440px-Shah_Rukh_Khan_graces_the_launch_of_new_Tag_Heuer_watch_collection_%28cropped%29.jpg"),
            # 1
            ("Aamir Khan", 1965, "Indian actor, director, and producer known for his perfectionistic approach to cinema.", None),
            # 2
            ("Deepika Padukone", 1986, "Indian actress and one of the highest-paid actresses in the world.", None),
            # 3
            ("Rajkumar Hirani", 1962, "Indian film director known for heartwarming comedy-dramas like 3 Idiots and PK.", None),
            # 4
            ("Sanjay Leela Bhansali", 1963, "Indian filmmaker renowned for grand sets, visual opulence, and epic love stories.", None),
            # 5
            ("Amitabh Bachchan", 1942, "Legendary Indian actor, the 'Shahenshah' of Bollywood with a career spanning 50+ years.", None),
            # 6
            ("Kareena Kapoor", 1980, "Indian actress and style icon, part of the Kapoor film dynasty.", None),
            # 7
            ("A.R. Rahman", 1967, "Oscar-winning Indian music composer, singer, and songwriter known as the Mozart of Madras.", None),
            # 8
            ("Ranveer Singh", 1985, "Indian actor known for intense roles and eclectic personal style.", None),
            # 9
            ("Alia Bhatt", 1993, "Indian actress who debuted young and became a critically acclaimed star.", None),
            # 10
            ("S.S. Rajamouli", 1973, "Indian filmmaker known for the epic Baahubali series and the global hit RRR.", None),
            # 11
            ("Ram Charan", 1985, "Indian actor and producer, son of Chiranjeevi, known for his role in RRR.", None),
            # 12
            ("Jr NTR", 1983, "Indian actor known for intense performances in Telugu cinema and RRR.", None),
            # 13
            ("Prabhas", 1979, "Indian actor who became a pan-India star through the Baahubali franchise.", None),
            # 14
            ("Christopher Nolan", 1970, "British-American filmmaker known for mind-bending narratives and practical effects.", None),
            # 15
            ("Leonardo DiCaprio", 1974, "American actor and film producer, Academy Award winner for The Revenant.", None),
            # 16
            ("Cillian Murphy", 1976, "Irish actor known for nuanced, complex roles in Inception, Oppenheimer, and Peaky Blinders.", None),
            # 17
            ("Mani Ratnam", 1956, "Indian director acclaimed for Tamil cinema and Bollywood crossovers like Dil Se and Bombay.", None),
            # 18 — Farhan Akhtar (replaces old Farah Khan entry)
            ("Farhan Akhtar", 1974, "Indian filmmaker and actor who directed Dil Chahta Hai and Don, and starred in ZNMD.", None),
            # 19
            ("Zoya Akhtar", 1972, "Indian filmmaker known for nuanced urban stories like Gully Boy and Zindagi Na Milegi Dobara.", None),
            # 20
            ("Vijay Thalapathy", 1974, "Indian actor and one of the biggest stars in Tamil cinema.", None),
            # 21
            ("Rajinikanth", 1950, "Indian actor and cultural icon dubbed 'Superstar', one of Asia's biggest film stars.", None),
            # 22
            ("Kamal Haasan", 1954, "Legendary Indian actor, director, and politician known for versatile performances.", None),
            # 23 — NEW
            ("Karan Johar", 1972, "Indian filmmaker, producer, and television personality known for glossy family dramas.", None),
            # 24 — NEW
            ("Hrithik Roshan", 1974, "Indian actor known for his dancing ability and intense roles in Koi Mil Gaya and ZNMD.", None),
            # 25 — NEW
            ("Kangana Ranaut", 1987, "Indian actress known for powerful performances in Queen, Tanu Weds Manu, and Manikarnika.", None),
            # 26 — NEW
            ("Nitesh Tiwari", 1973, "Indian director known for Dangal and Chhichhore.", None),
            # 27 — NEW
            ("M.M. Keeravani", 1961, "Indian music composer who scored Baahubali and won an Oscar for 'Naatu Naatu' from RRR.", None),
            # 28 — NEW
            ("Saif Ali Khan", 1970, "Indian actor and producer, known for Dil Chahta Hai, Omkara, and Sacred Games.", None),
            # 29 — NEW
            ("Shankar", 1963, "Indian director known for big-budget spectacle films like Enthiran, 2.0, and Ponniyin Selvan.", None),
            # 30 — NEW
            ("Lokesh Kanagaraj", 1988, "Indian director known for Kaithi and Vikram, architect of the Lokesh Cinematic Universe.", None),
        ]
        people = []
        for name, birth_year, bio, photo_url in people_data:
            p = Person(name=name, birth_year=birth_year, bio=bio, photo_url=photo_url)
            db.add(p)
            people.append(p)
        db.flush()

        # --- Movies ---
        movies_data = [
            # idx 0
            ("3 Idiots", 2009, ["Comedy", "Drama"], "Two friends search for their long-lost companion while recalling their days at an engineering college.", 170, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/d/df/3_idiots_poster.jpg"),
            # idx 1
            ("Chennai Express", 2013, ["Action", "Comedy", "Romance"], "A man on his way to immerse his grandfather's ashes meets a feisty Tamil girl.", 141, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/1/1b/Chennai_Express.jpg"),
            # idx 2
            ("Dilwale Dulhania Le Jayenge", 1995, ["Drama", "Romance"], "Two young people fall in love on a trip across Europe but must face family disapproval.", 189, "Hindi", "U", "https://upload.wikimedia.org/wikipedia/en/1/1d/Dilwale_Dulhania_Le_Jayenge_poster.jpg"),
            # idx 3
            ("Bajirao Mastani", 2015, ["Drama", "History", "Romance"], "The passionate love story between Maratha warrior Bajirao and his second wife Mastani.", 158, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/8/8e/Bajirao_Mastani_poster.jpg"),
            # idx 4
            ("Padmaavat", 2018, ["Drama", "History"], "Rajput queen Padmavati is known for her beauty, and a sultan sets out to possess her.", 164, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/7/73/Padmaavat_poster.jpg"),
            # idx 5
            ("Baahubali: The Beginning", 2015, ["Action", "Adventure", "Drama"], "An adventurer finds himself drawn into a conflict between two warring kingdoms.", 159, "Telugu", "UA", "https://upload.wikimedia.org/wikipedia/en/5/5f/Baahubali_The_Beginning_poster.jpg"),
            # idx 6
            ("Baahubali: The Conclusion", 2017, ["Action", "Adventure", "Drama"], "The legend of Baahubali reaches its epic conclusion with stunning action sequences.", 167, "Telugu", "UA", "https://upload.wikimedia.org/wikipedia/en/9/93/Baahubali_2_The_Conclusion_poster.jpg"),
            # idx 7
            ("RRR", 2022, ["Action", "Drama", "History"], "A fictional story about two Indian revolutionaries who fight the British Raj.", 187, "Telugu", "UA", "https://upload.wikimedia.org/wikipedia/en/2/2b/RRR_Poster.jpg"),
            # idx 8
            ("Inception", 2010, ["Action", "Sci-Fi", "Thriller"], "A thief who steals corporate secrets through the use of dream-sharing technology.", 148, "English", "UA", "https://upload.wikimedia.org/wikipedia/en/2/2e/Inception_%282010%29_theatrical_poster.jpg"),
            # idx 9
            ("Oppenheimer", 2023, ["Biography", "Drama", "History"], "The story of J. Robert Oppenheimer's role in the development of the atomic bomb.", 180, "English", "A", "https://upload.wikimedia.org/wikipedia/en/4/4a/Oppenheimer_%28film%29.jpg"),
            # idx 10
            ("Dangal", 2016, ["Biography", "Drama", "Sport"], "Former wrestler Mahavir Singh Phogat trains his daughters to become world-class wrestlers.", 161, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/6/sixty/Dangal_Poster.jpg"),
            # idx 11
            ("PK", 2014, ["Comedy", "Drama", "Sci-Fi"], "An alien on Earth loses his remote and questions religious customs while searching for it.", 153, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/d/da/PK_poster.jpg"),
            # idx 12
            ("Gully Boy", 2019, ["Drama", "Music"], "A street rapper from Mumbai's slums fights his circumstances to find his voice.", 154, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/5/56/Gully_Boy_poster.jpg"),
            # idx 13
            ("Gangubai Kathiawadi", 2022, ["Biography", "Crime", "Drama"], "The story of a woman sold into prostitution who became a powerful voice for her community.", 152, "Hindi", "A", "https://upload.wikimedia.org/wikipedia/en/8/89/Gangubai_Kathiawadi_film_poster.jpg"),
            # idx 14
            ("Don", 2006, ["Action", "Crime", "Thriller"], "A simple man is asked to impersonate an international criminal known as Don.", 155, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/1/14/Don_%282006_Hindi_film%29_poster.jpg"),
            # idx 15
            ("Interstellar", 2014, ["Adventure", "Drama", "Sci-Fi"], "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.", 169, "English", "UA", "https://upload.wikimedia.org/wikipedia/en/b/bc/Interstellar_film_poster.jpg"),
            # idx 16
            ("The Dark Knight", 2008, ["Action", "Crime", "Drama"], "Batman faces the Joker, a criminal mastermind who plunges Gotham into chaos.", 152, "English", "UA", "https://upload.wikimedia.org/wikipedia/en/8/8a/The_Dark_Knight_%282008_film%29.jpg"),
            # idx 17
            ("Lagaan", 2001, ["Drama", "Musical", "Sport"], "Villagers in colonial India challenge their British rulers to a game of cricket to avoid taxes.", 224, "Hindi", "U", "https://upload.wikimedia.org/wikipedia/en/4/43/Lagaan.jpg"),
            # idx 18
            ("Dil Chahta Hai", 2001, ["Comedy", "Drama", "Romance"], "Three inseparable friends go on a road trip and find love and meaning in life.", 183, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/4/4c/Dil_Chahta_Hai.jpg"),
            # idx 19
            ("Queen", 2014, ["Adventure", "Drama", "Romance"], "A sheltered Delhi girl embarks on her honeymoon alone after being jilted and finds herself.", 146, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/4/45/QueenMoviePoster7thMarch.jpg"),
            # idx 20
            ("Zindagi Na Milegi Dobara", 2011, ["Adventure", "Drama", "Romance"], "Three friends go on a road trip across Spain and confront their deepest fears.", 155, "Hindi", "UA", "https://upload.wikimedia.org/wikipedia/en/1/17/Zindagi_Na_Milegi_Dobara.jpg"),
            # idx 21
            ("Taare Zameen Par", 2007, ["Drama", "Family"], "A dyslexic child struggles in school until a new art teacher recognizes his talent.", 165, "Hindi", "U", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSLKhA9TsgkzaYnU6vWozqFidVVhRcNxqJywYjdYjNVnRftciOf"),
            # idx 22
            ("Kabhi Khushi Kabhie Gham", 2001, ["Drama", "Romance"], "A wealthy patriarch's estranged family is reunited after years of separation.", 210, "Hindi", "U", "https://upload.wikimedia.org/wikipedia/en/5/55/Kabhi_Khushi_Kabhie_Gham..._poster.jpg"),
            # idx 23
            ("Mughal-E-Azam", 1960, ["Drama", "History", "Musical"], "The legendary love story of Mughal Prince Salim and the courtesan Anarkali.", 197, "Hindi", "U", "https://upload.wikimedia.org/wikipedia/en/8/8b/Mughal-e-Azam.jpg"),
            # idx 24
            ("Mother India", 1957, ["Drama"], "A poverty-stricken village woman raises her sons through hardship and moral courage.", 172, "Hindi", "U", "https://upload.wikimedia.org/wikipedia/en/7/70/Mother_India_poster.jpg"),
            # idx 25
            ("Dil Se", 1998, ["Drama", "Romance", "Thriller"], "A radio journalist falls passionately in love with a mysterious woman involved in a militant group.", 163, "Hindi", "A", "https://upload.wikimedia.org/wikipedia/en/7/7a/Dil_Se_poster.jpg"),
            # idx 26
            ("Enthiran", 2010, ["Action", "Romance", "Sci-Fi"], "A scientist creates a humanoid robot that develops emotions and falls in love, with dangerous consequences.", 177, "Tamil", "UA", "https://upload.wikimedia.org/wikipedia/en/0/0f/Enthiran_poster.jpg"),
            # idx 27
            ("Vikram", 2022, ["Action", "Crime", "Thriller"], "A special agent reassembles a defunct Black-ops team to track down a gang of masked killers.", 174, "Tamil", "A", "https://upload.wikimedia.org/wikipedia/en/a/a5/Vikram_2022_poster.jpg"),
        ]
        movies = []
        for title, year, genres, plot, runtime, lang, cert, poster in movies_data:
            m = Movie(
                title=title,
                release_year=year,
                genres=genres,
                plot_summary=plot,
                runtime_minutes=runtime,
                language=lang,
                certificate=cert,
                poster_url=poster
            )
            db.add(m)
            movies.append(m)
        db.flush()

        # --- Credits ---
        # (person_idx, movie_idx, role_type, character_name)
        # All credits are factually verified.
        credits_data = [
            # 3 Idiots (0) — Aamir Khan as Rancho, Hirani directed; Shantanu Moitra did music (not in our list)
            (1, 0, "actor", "Rancho"),
            (3, 0, "director", None),

            # Chennai Express (1) — SRK and Deepika Padukone
            (0, 1, "actor", "Rahul Mithaiwala"),
            (2, 1, "actor", "Meenamma"),

            # DDLJ (2) — SRK as Raj, Kajol as Simran (Kajol not in our list)
            (0, 2, "actor", "Raj Malhotra"),

            # Bajirao Mastani (3) — SLB directed, Ranveer as Bajirao, Deepika as Mastani; Priyanka as Kashibai (not in list)
            (4, 3, "director", None),
            (8, 3, "actor", "Bajirao"),
            (2, 3, "actor", "Mastani"),

            # Padmaavat (4) — SLB directed, Ranveer as Alauddin Khilji, Deepika as Padmavati
            (4, 4, "director", None),
            (8, 4, "actor", "Alauddin Khilji"),
            (2, 4, "actor", "Padmavati"),

            # Baahubali: The Beginning (5) — Rajamouli directed, Prabhas as Baahubali, M.M. Keeravani music
            (10, 5, "director", None),
            (13, 5, "actor", "Baahubali"),
            (27, 5, "music_director", None),

            # Baahubali: The Conclusion (6)
            (10, 6, "director", None),
            (13, 6, "actor", "Baahubali"),
            (27, 6, "music_director", None),

            # RRR (7) — Rajamouli directed, Ram Charan as Alluri Raju, Jr NTR as Komaram Bheem, Keeravani music
            (10, 7, "director", None),
            (11, 7, "actor", "Alluri Sitarama Raju"),
            (12, 7, "actor", "Komaram Bheem"),
            (27, 7, "music_director", None),

            # Inception (8) — Nolan directed, DiCaprio as Dom Cobb, Cillian Murphy as Robert Fischer
            (14, 8, "director", None),
            (15, 8, "actor", "Dom Cobb"),
            (16, 8, "actor", "Robert Fischer"),

            # Oppenheimer (9) — Nolan directed, Cillian Murphy as Oppenheimer
            (14, 9, "director", None),
            (16, 9, "actor", "J. Robert Oppenheimer"),

            # Dangal (10) — Nitesh Tiwari directed, Aamir as Mahavir Singh Phogat
            (1, 10, "actor", "Mahavir Singh Phogat"),
            (26, 10, "director", None),

            # PK (11) — Hirani directed, Aamir as PK
            (3, 11, "director", None),
            (1, 11, "actor", "PK"),

            # Gully Boy (12) — Zoya Akhtar directed, Ranveer as Murad
            (8, 12, "actor", "Murad Ahmed"),
            (19, 12, "director", None),

            # Gangubai Kathiawadi (13) — SLB directed, Alia as Gangubai
            (9, 13, "actor", "Gangubai"),
            (4, 13, "director", None),

            # Don (14) — Farhan Akhtar directed, SRK as Don/Vijay
            (0, 14, "actor", "Don / Vijay"),
            (18, 14, "director", None),

            # Interstellar (15) — Nolan directed; Matthew McConaughey as Cooper (not in list)
            (14, 15, "director", None),

            # The Dark Knight (16) — Nolan directed, Cillian Murphy as Scarecrow
            (14, 16, "director", None),
            (16, 16, "actor", "Scarecrow"),

            # Lagaan (17) — Aamir as Bhuvan, AR Rahman music (won National Award)
            (1, 17, "actor", "Bhuvan"),
            (7, 17, "music_director", None),

            # Dil Chahta Hai (18) — Farhan Akhtar directed, Aamir as Akash, Saif Ali Khan as Sameer
            (18, 18, "director", None),
            (1, 18, "actor", "Akash"),
            (28, 18, "actor", "Sameer"),

            # Queen (19) — Kangana Ranaut as Rani; Vikas Bahl directed (not in list)
            (25, 19, "actor", "Rani"),

            # ZNMD (20) — Zoya Akhtar directed, Hrithik Roshan as Kabir, Farhan Akhtar as Imraan
            (19, 20, "director", None),
            (24, 20, "actor", "Kabir"),
            (18, 20, "actor", "Imraan"),

            # Taare Zameen Par (21) — Aamir Khan as actor AND director
            (1, 21, "actor", "Ram Shankar Nikumbh"),
            (1, 21, "director", None),

            # K3G (22) — Karan Johar directed, SRK as Rahul, Kareena as Poo, Amitabh as Yash
            (23, 22, "director", None),
            (0, 22, "actor", "Rahul Raichand"),
            (6, 22, "actor", "Poo"),
            (5, 22, "actor", "Yash Raichand"),

            # Mughal-E-Azam (23) — classic; K. Asif directed, Prithviraj Kapoor starred (neither in list)
            # Mother India (24) — classic; Mehboob Khan directed, Nargis starred (neither in list)

            # Dil Se (25) — Mani Ratnam directed, AR Rahman music, SRK as Amar
            (17, 25, "director", None),
            (7, 25, "music_director", None),
            (0, 25, "actor", "Amar"),

            # Enthiran (26) — Shankar directed, AR Rahman music, Rajinikanth as Chitti/Vaseegaran
            (29, 26, "director", None),
            (7, 26, "music_director", None),
            (21, 26, "actor", "Chitti / Vaseegaran"),

            # Vikram (27) — Lokesh Kanagaraj directed, Kamal Haasan as Vikram, Vijay as Rolex
            (30, 27, "director", None),
            (22, 27, "actor", "Vikram"),
            (20, 27, "actor", "Rolex"),
        ]
        seen_credits = set()
        for person_idx, movie_idx, role, char_name in credits_data:
            key = (person_idx, movie_idx, role)
            if key in seen_credits:
                continue
            seen_credits.add(key)
            c = Credit(
                person_id=people[person_idx].id,
                movie_id=movies[movie_idx].id,
                role_type=role,
                character_name=char_name
            )
            db.add(c)
        db.flush()

        # --- Ratings (generate rich data for Top Rated and Trending) ---
        random.seed(42)
        now = datetime.now(timezone.utc)

        score_profiles = {
            0:  (8, 10),  # 3 Idiots - excellent
            1:  (6, 9),   # Chennai Express - good
            2:  (8, 10),  # DDLJ - excellent
            3:  (7, 10),  # Bajirao - great
            4:  (6, 9),   # Padmaavat - good
            5:  (7, 10),  # Baahubali 1 - great
            6:  (8, 10),  # Baahubali 2 - excellent
            7:  (8, 10),  # RRR - excellent
            8:  (8, 10),  # Inception - excellent
            9:  (8, 10),  # Oppenheimer - excellent
            10: (8, 10),  # Dangal - excellent
            11: (7, 10),  # PK - great
            12: (7, 9),   # Gully Boy - good
            13: (7, 9),   # Gangubai - good
            14: (7, 9),   # Don - good
            15: (8, 10),  # Interstellar - excellent
            16: (9, 10),  # Dark Knight - masterpiece
            17: (8, 10),  # Lagaan - excellent
            18: (7, 10),  # Dil Chahta Hai - great
            19: (7, 9),   # Queen - good
            20: (7, 10),  # ZNMD - great
            21: (8, 10),  # Taare Zameen Par - excellent
            22: (6, 9),   # K3G - good
            23: (8, 10),  # Mughal-E-Azam - classic masterpiece
            24: (7, 10),  # Mother India - classic
            25: (8, 10),  # Dil Se - excellent (AR Rahman, Mani Ratnam)
            26: (7, 10),  # Enthiran - great
            27: (8, 10),  # Vikram - excellent
        }

        for movie_idx, movie in enumerate(movies):
            num_ratings = random.randint(12, 20)
            min_s, max_s = score_profiles.get(movie_idx, (6, 9))
            for i in range(min(num_ratings, len(users))):
                score = random.randint(min_s, max_s)
                days_ago = random.randint(0, 14)
                r = Rating(
                    user_id=users[i].id,
                    movie_id=movie.id,
                    score=score,
                    created_at=now - timedelta(days=days_ago)
                )
                db.add(r)
                movie.rating_sum += score
                movie.rating_count += 1
            if movie.rating_count > 0:
                movie.average_rating = round(movie.rating_sum / movie.rating_count, 2)
        db.flush()

        # --- Reviews ---
        review_templates = [
            "An absolute masterpiece. One of the finest films ever made. Every frame is perfect.",
            "Brilliantly crafted with stunning performances. A must-watch for every cinema lover.",
            "Engaging from start to finish. The story, direction, and music all come together beautifully.",
            "A visual spectacle with heart. The performances are unforgettable.",
            "Good entertainment but could have been shorter. Still worth your time.",
            "Decent movie with some great moments. Not perfect but enjoyable.",
            "The music elevates every scene. A cinematic experience like no other.",
            "Deeply moving. Left me thinking about it for days after watching.",
            "Technically brilliant — the cinematography and production design are world-class.",
            "A bold, ambitious film that pays off completely. Highly recommended.",
        ]
        for i, movie in enumerate(movies[:18]):
            num_reviews = random.randint(2, 4)
            for j in range(min(num_reviews, len(users))):
                rev = Review(
                    user_id=users[j].id,
                    movie_id=movie.id,
                    rating=random.randint(7, 10),
                    text=review_templates[(i + j) % len(review_templates)],
                    helpful_votes=random.randint(0, 100)
                )
                db.add(rev)

        # --- Sample Watchlist ---
        watchlist_pairs = [(0, 0), (0, 7), (0, 8), (1, 2), (1, 15), (2, 9)]
        for user_idx, movie_idx in watchlist_pairs:
            wl = WatchlistItem(user_id=users[user_idx].id, movie_id=movies[movie_idx].id)
            db.add(wl)

        db.commit()
        print("✅ Seed data inserted successfully!")
        print(f"   {len(users)} users | {len(people)} people | {len(movies)} movies | {len(credits_data)} credits")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
