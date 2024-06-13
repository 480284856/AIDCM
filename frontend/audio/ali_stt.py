import time
import pyaudio
import threading
import dashscope
import streamlit as st

from threading import Timer
from streamlit.elements.widgets.button import *
from streamlit.delta_generator import DeltaGenerator
from streamlit.elements.widgets.button import ButtonMixin
from streamlit.runtime.scriptrunner import add_script_run_ctx
from dashscope.common.error import InvalidParameter,InvalidTask
from dashscope.audio.asr.recognition import Recognition,RecognitionCallback,RecognitionResult

# 重新实现button方法，让其能够固定在聊天框底部
@gather_metrics("button")
def button(
    self,
    label: str,
    key: Key | None = None,
    help: str | None = None,
    on_click: WidgetCallback | None = None,
    args: WidgetArgs | None = None,
    kwargs: WidgetKwargs | None = None,
    *,  # keyword-only arguments:
    type: Literal["primary", "secondary"] = "secondary",
    disabled: bool = False,
    use_container_width: bool = False,
    fix_to_buttom: bool = False,
) -> bool:
    r"""Display a button widget.

    Parameters
    ----------
    label : str
        A short label explaining to the user what this button is for.
        The label can optionally contain Markdown and supports the following
        elements: Bold, Italics, Strikethroughs, Inline Code, and Emojis.

        This also supports:

        * Emoji shortcodes, such as ``:+1:``  and ``:sunglasses:``.
            For a list of all supported codes,
            see https://share.streamlit.io/streamlit/emoji-shortcodes.

        * LaTeX expressions, by wrapping them in "$" or "$$" (the "$$"
            must be on their own lines). Supported LaTeX functions are listed
            at https://katex.org/docs/supported.html.

        * Colored text and background colors for text, using the syntax
            ``:color[text to be colored]`` and ``:color-background[text to be colored]``,
            respectively. ``color`` must be replaced with any of the following
            supported colors: blue, green, orange, red, violet, gray/grey, rainbow.
            For example, you can use ``:orange[your text here]`` or
            ``:blue-background[your text here]``.

        Unsupported elements are unwrapped so only their children (text contents) render.
        Display unsupported elements as literal characters by
        backslash-escaping them. E.g. ``1\. Not an ordered list``.
    key : str or int
        An optional string or integer to use as the unique key for the widget.
        If this is omitted, a key will be generated for the widget
        based on its content. Multiple widgets of the same type may
        not share the same key.
    help : str
        An optional tooltip that gets displayed when the button is
        hovered over.
    on_click : callable
        An optional callback invoked when this button is clicked.
    args : tuple
        An optional tuple of args to pass to the callback.
    kwargs : dict
        An optional dict of kwargs to pass to the callback.
    type : "secondary" or "primary"
        An optional string that specifies the button type. Can be "primary" for a
        button with additional emphasis or "secondary" for a normal button. Defaults
        to "secondary".
    disabled : bool
        An optional boolean, which disables the button if set to True. The
        default is False.
    use_container_width: bool
        An optional boolean, which makes the button stretch its width to match the parent container.

    Returns
    -------
    bool
        True if the button was clicked on the last run of the app,
        False otherwise.

    Example
    -------
    >>> import streamlit as st
    >>>
    >>> st.button("Reset", type="primary")
    >>> if st.button("Say hello"):
    ...     st.write("Why hello there")
    ... else:
    ...     st.write("Goodbye")

    .. output::
        https://doc-buton.streamlit.app/
        height: 220px

    """
    key = to_key(key)
    ctx = get_script_run_ctx()

    # Checks whether the entered button type is one of the allowed options - either "primary" or "secondary"
    if type not in ["primary", "secondary"]:
        raise StreamlitAPIException(
            'The type argument to st.button must be "primary" or "secondary". \n'
            f'The argument passed was "{type}".'
        )

    return self.dg._button(
        label,
        key,
        help,
        is_form_submitter=False,
        on_click=on_click,
        args=args,
        kwargs=kwargs,
        disabled=disabled,
        type=type,
        use_container_width=use_container_width,
        ctx=ctx,
        fix_to_buttom=fix_to_buttom
    )

def _button(
        self,
        label: str,
        key: str | None,
        help: str | None,
        is_form_submitter: bool,
        on_click: WidgetCallback | None = None,
        args: WidgetArgs | None = None,
        kwargs: WidgetKwargs | None = None,
        *,  # keyword-only arguments:
        type: Literal["primary", "secondary"] = "secondary",
        disabled: bool = False,
        use_container_width: bool = False,
        ctx: ScriptRunContext | None = None,
        fix_to_buttom: bool = False,
    ) -> bool:
        key = to_key(key)

        # Importing these functions here to avoid circular imports
        from streamlit.elements.utils import (
            check_cache_replay_rules,
            check_callback_rules,
            check_session_state_rules,
        )

        if not is_form_submitter:
            check_callback_rules(self.dg, on_click)
        check_cache_replay_rules()
        check_session_state_rules(default_value=None, key=key, writes_allowed=False)

        id = compute_widget_id(
            "button",
            user_key=key,
            label=label,
            key=key,
            help=help,
            is_form_submitter=is_form_submitter,
            type=type,
            use_container_width=use_container_width,
            page=ctx.page_script_hash if ctx else None,
        )

        # It doesn't make sense to create a button inside a form (except
        # for the "Form Submitter" button that's automatically created in
        # every form). We throw an error to warn the user about this.
        # We omit this check for scripts running outside streamlit, because
        # they will have no script_run_ctx.
        if runtime.exists():
            if is_in_form(self.dg) and not is_form_submitter:
                raise StreamlitAPIException(
                    f"`st.button()` can't be used in an `st.form()`.{FORM_DOCS_INFO}"
                )
            elif not is_in_form(self.dg) and is_form_submitter:
                raise StreamlitAPIException(
                    f"`st.form_submit_button()` must be used inside an `st.form()`.{FORM_DOCS_INFO}"
                )

        button_proto = ButtonProto()
        button_proto.id = id
        button_proto.label = label
        button_proto.default = False
        button_proto.is_form_submitter = is_form_submitter
        button_proto.form_id = current_form_id(self.dg)
        button_proto.type = type
        button_proto.use_container_width = use_container_width
        button_proto.disabled = disabled

        if help is not None:
            button_proto.help = dedent(help)

        serde = ButtonSerde()

        button_state = register_widget(
            "button",
            button_proto,
            user_key=key,
            on_change_handler=on_click,
            args=args,
            kwargs=kwargs,
            deserializer=serde.deserialize,
            serializer=serde.serialize,
            ctx=ctx,
        )

        if ctx:
            save_for_app_testing(ctx, id, button_state.value)
        
        if fix_to_buttom:
            from streamlit import _bottom
            _bottom._enqueue("button", button_proto)
        else:
            self.dg._enqueue("button", button_proto)

        return button_state.value

ButtonMixin.button = button
ButtonMixin._button = _button

# 回调函数，在某个条件下会调用其成员函数
class Callback(RecognitionCallback):
    def on_open(self) -> None:
        # 创建一个Pyaudio实例，用于与音频接口交互，比如打开、关闭音频流和获取设备信息。
        st.session_state.mic = pyaudio.PyAudio()
        # 创建一个音频流，用于从麦克风或其他音频源获取音频数据。
        st.session_state.stream = st.session_state.mic.open(
            format=pyaudio.paInt16,  # 音频数据格式,pyaudio.paInt16表示16位深度
            channels=1,              # 指定音频的声道数，1表示单声道Mono
            rate=16000,              # 指定音频的采样率，16000表示每秒采样1600次
            input=True)              # 指定该流用于输入，用于从麦克风或其他音频源获取音频数据
    
    def on_close(self) -> None:
        if st.session_state.stream:
            # 关闭音频流，防止继续读取数据
            st.session_state.stream.stop_stream()
            st.session_state.stream.close()
            st.session_state.stream = None
        if st.session_state.mic:
            # 关闭PyAudio实例，释放资源
            st.session_state.mic.terminate()
            st.session_state.mic = None
    
    def on_event(self, result: RecognitionResult) -> None:
        # 处理每一次转写结果
        st.session_state.transform_res = result
        print("RecognitionCallback sentence: ", result.get_sentence())

    def on_complete(self) -> None:
        # 当识别全部完成时调用
        print("RecognitionCallback on_complete：", st.session_state.transform_res.get_sentence())

# 父类调用Callback是在县城里调用的，所以得重新实现start方法
# 为这个调用callback的线程添加一个add_script_run_ctx，这样才能够在新的线程的隔离的环境中，保持st.session_state的值与主线程的一致。
class myRecognition(Recognition):
    def __init__(self, model: str, callback: RecognitionCallback, format: str, sample_rate: int, workspace: str = None, **kwargs):
        super().__init__(model, callback, format, sample_rate, workspace, **kwargs)
    
    def start(self, phrase_id: str = None, **kwargs):
        """Real-time speech recognition in asynchronous mode.
           Please call 'stop()' after you have completed recognition.

        Args:
            phrase_id (str, `optional`): The ID of phrase.

            **kwargs:
                disfluency_removal_enabled(bool, `optional`):
                    Filter mood words, turned off by default.
                diarization_enabled (bool, `optional`):
                    Speech auto diarization, turned off by default.
                speaker_count (int, `optional`): The number of speakers.
                timestamp_alignment_enabled (bool, `optional`):
                    Timestamp-alignment calibration, turned off by default.
                special_word_filter(str, `optional`): Sensitive word filter.
                audio_event_detection_enabled(bool, `optional`):
                    Audio event detection, turned off by default.

        Raises:
            InvalidParameter: This interface cannot be called again
                if it has already been started.
            InvalidTask: Task create failed.
        """
        assert self._callback is not None, 'Please set the callback to get the speech recognition result.'  # noqa E501

        if self._running:
            raise InvalidParameter('Speech recognition has started.')

        self._phrase = phrase_id
        self._kwargs.update(**kwargs)
        self._recognition_once = False
        self._worker = add_script_run_ctx(threading.Thread(target=self.__receive_worker))
        self._worker.start()
        if self._worker.is_alive():
            self._running = True
            self._callback.on_open()

            # If audio data is not received for 23 seconds, the timeout exits
            self._silence_timer = Timer(Recognition.SILENCE_TIMEOUT_S,
                                        self._silence_stop_timer)
            self._silence_timer.start()
        else:
            self._running = False
            raise InvalidTask('Invalid task, task create failed.') 

def session_state_variables():
    # 定义全局变量
    # 分别定义：
    # mic 麦克风对象
    # stream 音频流对象
    # recognition 语音识别对象
    # recognition_activte 语音识别是否激活的标志。把其放在session_state中，是因为第二次点击页面会重新执行整个程序，这样会把这个标志重置。
    # exit_program 程序是否需要推出的标志
    # lock 线程锁，用于同步操作。lock要放在session_state中，因为第二次点击页面会重新创建一个线程。
    # transform_res 存储Callback类每次转写的结果，当时别完成时，这个变量记录的就是最有一次完整的识别结果。

    if 'mic' not in st.session_state:
        st.session_state.mic = None
    
    if 'stream' not in st.session_state:
        st.session_state.stream = None
    
    if 'recognition' not in st.session_state:
        st.session_state.recognition = None

    if 'recognition_activte' not in st.session_state:
        st.session_state.recognition_activte = False

    if 'exit_program' not in st.session_state:
        st.session_state.exit_program = False

    if 'lock' not in st.session_state:
        st.session_state.lock = threading.Lock()

    if 'transform_res' not in st.session_state:
        st.session_state.transform_res = None

def lingji_stt_st() -> str:
    # 定义语音识别的函数

    # 不能够放在python文件的第一级执行，得每次都执行一遍。
    # 这里是子文件，不是主文件，Streamlit应该只会执行子文件里的被主文件调用的代码。
    # 当我刷新时，就相当于创建了一个新的session，但如果放在第一级的话，子文件里的这些if语句就不会被执行。
    session_state_variables()

    # 需要把创建的语音识别实例放在session_state中，因为每次运行整个程序时，如果不放入的话，
    # 就会重新创建一个新的语音识别实例，然后下面的代码会直接调用这个新的实例的.stop方法。
    if st.session_state.recognition is None:
        dashscope.api_key = 'sk-xx'
        st.session_state['recognition'] = myRecognition(
            model="paraformer-realtime-v1",  # 语音识别模型
            format='pcm',                    # 音频格式
            sample_rate=16000,               # 指定音频的采样率，16000表示每秒采样16000次。
            callback=Callback()              # 回调函数，在某个条件下会调用其成员函数。
        )
    
    # 添加触发按钮
    if 'dg' not in st.session_state:
        st.session_state.dg = DeltaGenerator()
    if ButtonMixin.button(st.session_state.dg, "🎤", fix_to_buttom=True):
        if not st.session_state.recognition_activte:           # 如果没有激活语音识别
            with st.session_state.lock:                        # 使用线程锁
                st.session_state.recognition_activte = True    # 设置识别激活标志
                st.session_state.recognition.start()           # 开始语音识别

                if 'stt_thread' not in st.session_state:
                    # 设置为守护进程，当主程序崩溃时，其也会自动结束。
                    st.session_state.stt_thread = threading.Thread(target=mystt, daemon=True)
                    st.session_state.stt_thread = add_script_run_ctx(st.session_state.stt_thread)
                    st.session_state.stt_thread.start()
        else:                                                  # 如果已经激活识别
            with st.session_state.lock:                        # 使用线程锁
                st.session_state.recognition_activte = False   # 取消识别激活标志
                st.session_state.recognition.stop()            # 停止语音识别
                st.session_state.recognition = None            # 因为stop时已经删除掉了一些组件，所以把语音识别实例删除掉，下次再重新创建。
            
            return st.session_state.transform_res.get_sentence()['text']
        
def mystt():
    while not st.session_state.exit_program:  # 主循环，直到设置退出标志
        # 使用线程锁，同一时刻，只有一个线程能够获得该锁，并执行锁下的代码，代码可以不同。
        # 防止主线程在执行循环的时候，stream或者是recognition对象突然变成None（执行if的时候还不是None，但进去if分支后就变成None了）
        # 所以在on_press函数的else分支那里需要用同一个锁。
        with st.session_state.lock:  
            if st.session_state.recognition_active and st.session_state.stream:  # 如果识别已经激活且音频流存在
                try:
                    data = st.session_state.stream.read(3200, exception_on_overflow=False)  # 读取音频数据
                    st.session_state.recognition.send_audio_frame(data)  # 发送音频数据进行识别
                except:
                    pass  # 忽略错误
        time.sleep(0.01)  # 每次循环后等待100毫秒，防止CPU占用过高  

if __name__ == "__main__":
    dg = DeltaGenerator()
    ButtonMixin.button(dg, "🎤", fix_to_buttom=True)