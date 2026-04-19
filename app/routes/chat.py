from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from .. import db, socketio
from ..models import ChatRoom, Message, User

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/')
@login_required
def list_rooms():
    rooms = ChatRoom.query.filter(
        (ChatRoom.participant1_id == current_user.id) |
        (ChatRoom.participant2_id == current_user.id)
    ).order_by(ChatRoom.created_at.desc()).all()
    return render_template('chat/list.html', rooms=rooms)


@chat_bp.route('/<int:room_id>')
@login_required
def room(room_id):
    chat_room = ChatRoom.query.get_or_404(room_id)
    if chat_room.participant1_id != current_user.id and \
            chat_room.participant2_id != current_user.id:
        abort(403)

    # Отмечаем сообщения как прочитанные
    Message.query.filter_by(room_id=room_id, is_read=False).filter(
        Message.sender_id != current_user.id
    ).update({'is_read': True})
    db.session.commit()

    messages = Message.query.filter_by(room_id=room_id).order_by(Message.created_at).all()
    other = chat_room.other_participant(current_user.id)
    return render_template('chat/room.html', room=chat_room, messages=messages, other=other)


@chat_bp.route('/start/<int:user_id>')
@login_required
def start_chat(user_id):
    if user_id == current_user.id:
        flash('Нельзя написать самому себе.', 'warning')
        return redirect(url_for('main.index'))

    other = User.query.get_or_404(user_id)
    room = ChatRoom.query.filter(
        ((ChatRoom.participant1_id == current_user.id) &
         (ChatRoom.participant2_id == user_id)) |
        ((ChatRoom.participant1_id == user_id) &
         (ChatRoom.participant2_id == current_user.id))
    ).first()

    if not room:
        room = ChatRoom(participant1_id=current_user.id, participant2_id=user_id)
        db.session.add(room)
        db.session.commit()

    return redirect(url_for('chat.room', room_id=room.id))


# SocketIO события

@socketio.on('join')
def handle_join(data):
    room_id = data.get('room')
    join_room(str(room_id))


@socketio.on('leave')
def handle_leave(data):
    room_id = data.get('room')
    leave_room(str(room_id))


@socketio.on('send_message')
def handle_message(data):
    from flask_login import current_user as cu
    room_id = data.get('room')
    content = data.get('content', '').strip()

    if not content or not room_id:
        return

    chat_room = ChatRoom.query.get(room_id)
    if not chat_room:
        return
    if chat_room.participant1_id != cu.id and chat_room.participant2_id != cu.id:
        return

    msg = Message(room_id=room_id, sender_id=cu.id, content=content)
    db.session.add(msg)
    db.session.commit()

    emit('receive_message', {
        'id': msg.id,
        'sender_id': cu.id,
        'sender_username': cu.username,
        'content': content,
        'created_at': msg.created_at.strftime('%H:%M'),
    }, room=str(room_id))
