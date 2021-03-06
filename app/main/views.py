# coding=utf-8
import base64
import os

from flask import current_app, jsonify
from flask import redirect, flash
from flask import render_template
from flask import request
from flask import url_for
from flask_login import login_required, current_user

from app import db
from app.main.forms import EditProfileForm
from app.models.models import User, TopicCategory, Topic, Question, Answer, Comments, Dynamic
from . import main
from app.lib import constant
from app.lib.pagination import base_pagination


@main.route("/")
@login_required
def index():
    topic_all = Topic.query.filter_by().all()
    return render_template("zheye.html", user=current_user, base64=base64,
                           topic_all=topic_all, index_show=current_user.current_user_index())


@main.route('/people/<username>')
def people(username):
    """个人资料界面"""
    user = User.query.filter_by(username=username).first_or_404()
    dynamics = Dynamic.search_dynamic(user.id)
    return render_template('user.html', user=user, base64=base64, dynamics=dynamics)


@main.route('/edit-profile', methods=['POST', 'GET'])
@login_required
def edit_profile():
    """编辑个人资料"""
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.sex = form.sex.data
        current_user.short_intr = form.short_intr.data
        current_user.school = form.school.data
        current_user.industry = form.industry.data
        current_user.discipline = form.discipline.data
        current_user.introduction = form.introduction.data
        db.session.add(current_user)
        db.session.commit()

        flash(constant.PROFILE_UPDATE)
        return redirect(url_for('main.people', username=current_user.username))

    form.name.data = current_user.name
    form.sex.data = current_user.sex or "man"
    form.short_intr.data = current_user.short_intr
    form.industry.data = current_user.industry
    form.school.data = current_user.school
    form.discipline.data = current_user.discipline
    form.introduction.data = current_user.introduction
    form.location.data = current_user.location

    return render_template('edit_profile.html', form=form, user=current_user, base64=base64)


@main.route('/follow/<username>')
@login_required
def follow(username):
    """关注某人"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify(error=constant.INVALID_USER)
    if user == current_user:
        return jsonify(constant.CANNOT_CON_MYSELF)
    if current_user.is_following(user):
        return jsonify(error=constant.ALREADY_CON)
    try:
        current_user.follow(user)
    except Exception as e:
        return jsonify(constant.FAIL)

    current_user.notify_follower(user.id, "follow_user")
    return jsonify(error="")


@main.route('/unfollow/<username>')
@login_required
def unfollow(username):
    """取消关注"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify(error=constant.INVALID_USER)
    if not current_user.is_following(user):
        return jsonify(error=constant.NO_CON)
    try:
        current_user.unfollow(user)
    except Exception as e:
        return jsonify(constant.FAIL)

    return jsonify(error="")


@main.route('/people/<username>/followers')
def followers(username):
    """显示username的关注者"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)

    # 获取分页对象
    pagination = base_pagination(user.followers, page, 'FLASKY_FOLLOWERS_PER_PAGE')
    follows = [{'user': item.follower}
               for item in pagination.items]
    who = u'我' if user == current_user else u'他'
    return render_template('user_followers.html', user=user, who=who,
                           endpoint='.followers', pagination=pagination,
                           follows=follows, base64=base64)


@main.route('/people/<username>/following')
def following(username):
    """分页显示username关注了谁"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = base_pagination(user.followed, page, 'FLASKY_FOLLOWERS_PER_PAGE')
    follows = [{'user': item.followed}
               for item in pagination.items]
    who = u'我' if user == current_user else u'他'
    return render_template('user_following.html', user=user, who=who,
                           endpoint='.following', pagination=pagination,
                           follows=follows, base64=base64)


@main.route('/people/<username>/asks')
def asks(username):
    """分页显示username提了哪些问题"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = base_pagination(user.questions, page, 'FLASKY_FOLLOWERS_PER_PAGE')

    return render_template('user_asks.html', user=user, base64=base64,
                           endpoint='.asks', pagination=pagination, items=pagination.items
                           )


@main.route('/people/<username>/answers')
def answers(username):
    """分页显示username回答了哪些问题"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = base_pagination(user.answers, page, 'FLASKY_FOLLOWERS_PER_PAGE')

    return render_template('user_answers.html', user=user, base64=base64,
                           endpoint='.answers', pagination=pagination, items=pagination.items)


@main.route('/people/<username>/activities')
def activities(username):
    """个人动态界面"""
    user = User.query.filter_by(username=username).first_or_404()
    dynamics = Dynamic.search_dynamic(user.id)
    return render_template('user.html', user=user, base64=base64, dynamics=dynamics)


@main.route('/people/images', methods=['POST'])
@login_required
def images():
    try:
        # 读取图片内容
        file = request.files['file'].read()
        if current_user.change_avatar(file):
            return redirect(url_for("main.people", username=current_user.username))
    except:
        pass
    # 头像修改失败，提示
    flash(constant.AVATAR_MODI_FAIL)
    return redirect(url_for("main.index"))


@main.route('/topics')
@login_required
def topics():
    """话题广场"""
    topic_cate = TopicCategory.query.all()  # 获取所有的话题类别
    cate_id = request.args.get("cate")  # 获取选中类别的id
    cate_selete = None
    if topic_cate:
        if cate_id:
            for cate in topic_cate:
                if cate.id == int(cate_id):
                    cate_selete = cate
                    break
        if not cate_selete:
            cate_selete = topic_cate[0]

    # return render_template("topics.html", base64=base64, user=current_user,
    #                        topic_cate=topic_cate, topics=topic_cate[0].topics)
    return render_template("topics.html", base64=base64, user=current_user,
                           topic_cate=topic_cate, cate_selete=cate_selete)


@main.route('/topic')
@login_required
def topic():
    """话题动态, 用户关注的话题"""
    topics = current_user.follow_topics.filter_by().all()  # 获取当前用户关注的话题
    topic_id = request.args.get("topic")  # 获取选择的话题的id
    topic_selete = None    # 选择的话题默认为None

    if topics:
        if topic_id:
            for topic in topics:
                if topic.topic.id == int(topic_id):
                    topic_selete = topic.topic
                    break
        if not topic_selete:
            topic_selete = topics[0].topic
            if topic_id:
                flash(constant.NOFOUND)
    return render_template("topic.html", base64=base64, user=current_user,
                           topics=topics, topic_selete=topic_selete)


# @main.route('/topics_search', methods=['POST'])
# @login_required
# def topics_search():
#     """查询选中话题类型下的所有话题"""
#     cate = request.form.get("topic_cate", None)
#     topic_cate = TopicCategory.query.filter_by(
#         category_name=cate).first()
#     if topic_cate:
#         # 返回的json数据包含四个参数:
#         # ```topic_name:话题名称```
#         # ```topic_desc:话题描述```
#         # ```id:话题索引```
#         # ```follow or unfollow```:是否被当前用户关注
#         return jsonify(topics=[[topic.topic_name, topic.topic_desc if topic.topic_desc else "",
#                                 str(topic.id), "follow" if current_user.is_following_topic(topic) else "unfollow"]
#                                for topic in topic_cate.topics])
#
#     return "error"


@main.route('/topic_all')
@login_required
def topic_all():
    """返回所有的话题，初始化问题中的话题选择框"""
    topics = Topic.query.filter_by().all()
    return jsonify(topics=[[topic.id, topic.topic_name] for topic in topics])


@main.route('/follow_topic/<topic_id>')
@login_required
def follow_topic(topic_id):
    """关注某个话题"""
    topic = Topic.query.filter_by(id=topic_id).first()
    if topic is None or current_user.is_following_topic(topic):
        return jsonify(error=constant.FAIL)

    # 关注话题
    try:
        current_user.follow_topic(topic)
    except Exception as e:
        return jsonify(error=constant.FAIL)

    current_user.add_dynamic(current_user.id, topic.id,
                             "topic")  # 增加关注话题动态记录
    current_user.notify_follower(topic.id, "follow_topic")
    return jsonify(error="")


@main.route('/unfollow_topic/<topic_id>')
@login_required
def unfollow_topic(topic_id):
    """取消关注某个话题"""
    topic = Topic.query.filter_by(id=topic_id).first()
    if topic is None or not current_user.is_following_topic(topic):
        return jsonify(error=constant.FAIL)

    # 取消关注
    try:
        current_user.unfollow_topic(topic)
        return jsonify(error="")
    except Exception as e:
        return jsonify(error=constant.FAIL)


@main.route('/follow_question/<question_id>')
@login_required
def follow_question(question_id):
    """关注某个问题"""
    question = Question.query.filter_by(id=question_id).first()
    if question is None or current_user.is_following_question(question):
        return jsonify(error=constant.FAIL)

    # 关注问题
    try:
        current_user.follow_question(question)
    except Exception as e:
        return jsonify(error=constant.FAIL)

    current_user.add_dynamic(current_user.id, question.id,
                             "question")  # 增加关注问题动态记录
    current_user.notify_follower(question.id, "follow_ques")
    return jsonify(error="")


@main.route('/unfollow_question/<question_id>')
@login_required
def unfollow_question(question_id):
    """取消关注某个问题"""
    question = Question.query.filter_by(id=question_id).first()
    if question is None or not current_user.is_following_question(question):
        return jsonify(error=constant.FAIL)

    # 取消关注
    try:
        current_user.unfollow_question(question)
        return jsonify(error="")
    except Exception as e:
        return jsonify(error=constant.FAIL)


@main.route('/submit_question', methods=['POST'])
@login_required
def submit_question():
    question = request.form.get("question")
    question_desc = request.form.get("question_desc")
    topic = request.form.get("topic")

    if topic == None or topic == "":
        return jsonify(error=constant.NOT_VALID_CHOICE)
    if len(question) > 60 or len(question_desc) > 500:
        return jsonify(error=constant.QUESTION_ERROR)

    # 添加问题
    result = Question.add_question(question, question_desc, topic, current_user.id)
    if not result:  # 操作失败
        return jsonify(error=constant.FAIL)

    current_user.follow_question(result)   # 提问者默认关注提出的问题
    current_user.notify_follower(result.id, "ask")
    return jsonify(result=result.id, error="")


@main.route('/submit_comment', methods=['POST'])
@login_required
def submit_comment():
    answer_id = request.form.get("answer_id")
    comment_body = request.form.get("comment_body")
    if not answer_id or len(comment_body) > 200:
        return jsonify(error=constant.COMMENT_ERROR)

    # 添加评论
    result = Comments.add_comment(answer_id, comment_body, current_user.id)
    if not result:
        return jsonify(error=constant.FAIL)
    return jsonify(error="", username=current_user.username, comment=comment_body)


@main.route('/topic/<int:id>')
@login_required
def topic_detail(id):
    """话题详细页面"""
    topic = Topic.query.get_or_404(id)

    return render_template("topic_detail.html", topic=topic, count=topic.follow_topics.count(),
                               base64=base64, questions_excellans=topic.questions_excellans())


@main.route('/question')
@login_required
def answer_question():
    """回答问题页面，默认显示关注话题下的问题"""
    topics_all = current_user.follow_topics.filter_by().all()
    return render_template("answer_questions.html", base64=base64, topics=topics_all)


@main.route('/question/following')
@login_required
def question_follow_all():
    questions = current_user.follow_questions.filter_by().all()
    return render_template("question_follow_all.html", questions=questions, base64=base64)


@main.route('/question/<int:id>')
@login_required
def question_detail(id):
    question = Question.query.get_or_404(id)

    question.ping()    # 增加问题的浏览次数
    return render_template("question_detail.html", question=question, base64=base64)


@main.route('/answer_submit', methods=['POST'])
def answer_submit():
    answer_body = request.form.get("write_answer")
    question_id = request.form.get("question_id")
    if not answer_body or not question_id:
        flash(constant.FAIL)
        return redirect(url_for('main.question_detail', id=question_id))

    flag = Answer.answer_question(current_user.id, question_id, answer_body)
    if not flag:
        flash(constant.FAIL)
    else:
        current_user.notify_follower(flag.id, "answer")
    return redirect(url_for('main.question_detail', id=question_id))


@main.route('/delete/answer/<int:id>')
def delete_answer(id):
    answer = Answer.query.filter_by(id=id).first()
    if answer is None or answer.users != current_user:
        return jsonify(error=constant.FAIL)
    db.session.delete(answer)
    try:
       db.session.commit()
       return jsonify(error="")
    except:
        return jsonify(error=constant.FAIL)


@main.route('/topic/<int:id>/followers')
def topic_followers(id):
    """显示某个话题的所有关注者"""
    topic = Topic.query.get_or_404(id)
    return render_template('alluser_follow_topic.html', base64=base64, topic=topic)


@main.route('/question/<int:id>/followers')
def question_followers(id):
    """显示某个话题的所有关注者"""
    question = Question.query.get_or_404(id)
    return render_template('alluser_follow_question.html', base64=base64, question=question)


@main.route('/explore')
@login_required
def explore():
    """发现"""
    recommend_quwstions = Question.recommend()
    return render_template("explore.html", base64=base64,
                           questions_excellans=recommend_quwstions)
