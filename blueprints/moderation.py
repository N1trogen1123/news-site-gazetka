import datetime

from data import db_session
from data.news import News
from data.users import User
from data.categories import Categories
from data.moderation_logs import ModerationLogs

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from flask import Blueprint, render_template, url_for, flash, request, redirect, abort

from flask_login import current_user, login_required

from decorators.is_banned import is_banned
from decorators.role_check import required_role

mod_bp = Blueprint('moder', __name__)

@mod_bp.route('/moderation')
@login_required
@required_role(['admin', 'moderator'])
@is_banned
def moderation():
    """Страница модерации новостей"""
    db_sess = db_session.create_session()
    try:
        stmt = (select(News)
                .where(News.status == 'На проверке')
                .options(
                    joinedload(News.author),
                    joinedload(News.category)))
        news_list = db_sess.scalars(stmt).all()

        return render_template('moderation.html', news_list=news_list, current_user=current_user)
    finally:
        db_sess.close()

@mod_bp.route('/moderate/<int:id>/<action>/')
@login_required
@required_role(['admin', 'moderator'])
@is_banned
def moderate_news(id, action, comment='Причина не указана'):
    """Обработка модерации новости (одобрение/отклонение)"""
    print(f"DEBUG: id={id}, action={action}, comment={comment}")
    
    db_sess = db_session.create_session()
    try:
        news = db_sess.scalars(select(News).where(News.id == id)).first()
        if not news:
            abort(404)

        if news.status != 'На проверке':
            return redirect(url_for('moder.moderation'))

        if action == 'approve':
            news.status = 'Опубликовано'
            message = f"Новость '{news.title}' одобрена"
        elif action == 'reject':
            news.status = 'Отклонено'
            message = f"Новость '{news.title}' отклонена"
        else:
            abort(400)

        # Создаем лог
        log = ModerationLogs(news_id=id, moderator_id=current_user.id, action=action, comment=comment, timestamp=datetime.datetime.now())
        db_sess.add(log)
        db_sess.commit()
        
        print(f"DEBUG: Лог добавлен: id={log.id}, comment={log.comment}")  # Отладка
        
        flash(message, 'success')
    except Exception as e:
        db_sess.rollback()
        print(f"Ошибка при модерации: {e}")
        flash(f'Ошибка при модерации: {str(e)}', 'danger')
    finally:
        db_sess.close()
    
    return redirect(url_for('moder.moderation'))


@mod_bp.route('/moderation/<int:id>', methods=['GET', 'POST'])
@login_required
@required_role(['admin', 'moderator'])
@is_banned
def moderate_news_id(id):
    db_sess = db_session.create_session()
    try:
        article = db_sess.get(News, id)

        if not article:
            flash('Новость не найдена', 'danger')
            return redirect(url_for('moder.moderation'))

        # Только новости на проверке можно модерировать
        if article.status != 'На проверке':
            flash('Эта новость уже была проверена', 'warning')
            return redirect(url_for('news.view_news', id=article.id))

        # Обработка POST-запроса (когда модератор нажал кнопку)
        if request.method == 'POST':
            # Забираем текст из обычного HTML поля <textarea name="comment">
            comment = request.form.get('comment', '').strip()

            # Проверяем, какая кнопка была нажата (сверяем name кнопки)
            if 'submit_approve' in request.form:
                article.status = 'Опубликовано'
                article.published_at = datetime.datetime.now()
                article.moderation_comment = comment if comment else None
                flash('Новость одобрена и опубликована', 'success')

            elif 'submit_reject' in request.form:
                article.status = 'Отклонено'
                article.moderation_comment = comment if comment else 'Отклонено без указания причины'
                flash('Новость отклонена', 'warning')

            article.moderated_at = datetime.datetime.now()
            article.moderated_by = current_user.id
            db_sess.commit()

            return redirect(url_for('moder.moderation'))

        # Если метод GET — просто отдаем страницу (передавать form=form больше не нужно!)
        return render_template('view_news.html', news=article)
    finally:
        db_sess.close()