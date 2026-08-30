from aiogram.fsm.state import State, StatesGroup


class SearchState(StatesGroup):
    waiting_query = State()


class FeedbackState(StatesGroup):
    waiting_text = State()


class PromoState(StatesGroup):
    waiting_code = State()


class ReviewState(StatesGroup):
    waiting_review = State()


class AddBookState(StatesGroup):
    choosing_genre = State()
    waiting_title = State()
    waiting_author = State()
    waiting_year = State()
    waiting_description = State()
    waiting_cover = State()
    waiting_file = State()
    confirm = State()


class EditBookState(StatesGroup):
    waiting_book_id = State()
    waiting_field = State()
    waiting_value = State()


class BroadcastState(StatesGroup):
    waiting_content = State()
    waiting_confirm = State()


class PromoCreateState(StatesGroup):
    waiting_code = State()
    waiting_reward = State()
    waiting_uses = State()


class QuizAddState(StatesGroup):
    waiting_book_id = State()
    waiting_question = State()
    waiting_options = State()
    waiting_correct = State()


class GenreAddState(StatesGroup):
    waiting_name_uz = State()
    waiting_name_ru = State()
    waiting_name_en = State()


class SetTextState(StatesGroup):
    waiting_text = State()


class SetCoverState(StatesGroup):
    waiting_photo = State()


class BlockUserState(StatesGroup):
    waiting_id = State()
