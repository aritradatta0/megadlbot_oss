import base64
import os
import secrets

import aiofiles
from pyrogram import emoji, Client
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ForceReply

from mega.database.users import MegaUsers
from mega.helpers.gdrive import Gdrive
from .. import filters


@Client.on_message(filters.command("dldsettings", prefixes=["/"]))
async def dld_settings_handler(c: Client, m: Message):
    user_details = await MegaUsers().get_user(m.from_user.id)
    await m.reply_text(
        f"Your Current Settings are: \n"
        f"{emoji.GEAR} Settings: {user_details['dld_settings']} \n"
        f"{emoji.FRAMED_PICTURE} Custom Thumbnail: "
        f"{'Set' if user_details['custom_thumbnail'] else None}",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text=f"{emoji.WRENCH} Change Download Settings",
                                      callback_data=f"dlsettings_{m.chat.id}")],
                [InlineKeyboardButton(text=f"{emoji.VIDEO_CAMERA} Set a Custom Thumbnail",
                                      callback_data=f"thumbnail_{m.chat.id}")],
                [InlineKeyboardButton(text=f"{emoji.OPEN_MAILBOX_WITH_RAISED_FLAG} Attach Google Drive",
                                      callback_data=f"googleset_{m.chat.id}")]
            ]
        )
    )


@Client.on_callback_query(filters.callback_query("dlsettings"), group=3)
async def callback_query_dld_settings_handler(c: Client, cb: CallbackQuery):
    await cb.answer()

    await cb.message.edit_reply_markup(
        InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text=f"{emoji.PAPERCLIP} Force Document",
                                      callback_data="f-docs")],
                [InlineKeyboardButton(text=f"{emoji.BRIEFCASE} Force Document w Thumbnail",
                                      callback_data="ct-docs")],
                [InlineKeyboardButton(text=f"{emoji.VIDEOCASSETTE} Video w Thumbnail",
                                      callback_data="ct-videos")],
            ]
        )
    )


@Client.on_callback_query(filters.callback_query("thumbnail"), group=4)
async def callback_query_thumbnail_handler(c: Client, cb: CallbackQuery):
    await cb.answer()

    await cb.message.reply_text(
        f"CST_{cb.message.message_id}\n"
        f"As a reply to this message, send me the Photo/Image you wish to set as a custom thumbnail for "
        f"your uploads/downloads.",
        reply_markup=ForceReply(True)
    )


@Client.on_message(filters.reply & filters.private & filters.photo, group=2)
async def thumbnail_reply_msg_handler(c: Client, m: Message):
    func_message_obj = str(m.reply_to_message.text).splitlines()[0].split("_")
    temp_img_file = f"working_dir/{secrets.token_hex(2)}.jpg"

    if len(func_message_obj) > 1:
        func = func_message_obj[0]

        if func == "CST":
            await c.download_media(message=m.photo, file_name=temp_img_file)

            async with aiofiles.open(f"mega/{temp_img_file}", mode='rb') as thumb:
                base64_thumb = base64.b64encode(await thumb.read())

            await MegaUsers().update_cst_thumb(m.from_user.id, base64_thumb)

            if os.path.exists(f"mega/{temp_img_file}"):
                os.remove(f"mega/{temp_img_file}")
            await m.reply_text(
                "Your custom thumbnail has been set!"
            )


@Client.on_callback_query(filters.callback_query("f-docs", payload=False))
async def force_docs_cb_handler(c: Client, cb: CallbackQuery):
    await MegaUsers().update_dld_settings(cb.message.chat.id, "f-docs")
    await cb.answer("Your settings has been updated to Force Document")


@Client.on_callback_query(filters.callback_query("ct-docs", payload=False))
async def thumbnail_docs_cb_handler(c: Client, cb: CallbackQuery):
    user_details = await MegaUsers().get_user(cb.message.chat.id)
    if user_details['custom_thumbnail'] is None:
        await c.send_message(
            chat_id=cb.message.chat.id,
            text="You cannot set your settings to Force Document w Thumbnail while you haven't told me the "
                 "Thumbnail I should use! Set a Custom Thumbnail via settings first!!!"
        )
        await cb.answer()
    else:
        await MegaUsers().update_dld_settings(cb.message.chat.id, "ct-docs")
        await cb.answer("Your settings has been updated to Force Document w Thumbnail")


@Client.on_callback_query(filters.callback_query("ct-videos", payload=False))
async def ct_videos_cb_handler(c: Client, cb: CallbackQuery):
    user_details = await MegaUsers().get_user(cb.message.chat.id)
    if user_details['custom_thumbnail'] is None:
        await c.send_message(
            chat_id=cb.message.chat.id,
            text="You cannot set your settings to Video w Thumbnail while you haven't told me the "
                 "Thumbnail I should use! Set a Custom Thumbnail via settings first!!!"
        )
        await cb.answer()
    else:
        await MegaUsers().update_dld_settings(cb.message.chat.id, "ct-videos")
        await cb.answer("Your settings has been updated to Video w Thumbnail")


@Client.on_callback_query(filters.callback_query("googleset"), group=5)
async def googleset_cb_handler(c: Client, cb: CallbackQuery):
    user_details = await MegaUsers().get_user(cb.message.chat.id)

    if "gdrive_key" in user_details:
        await c.send_message(
            chat_id=cb.message.chat.id,
            text=f"GDV_{cb.message.message_id}\n"
                 "You had already set a gdrive key, to replace it as a reply to this message send me the new "
                 "service account key"
        )
    else:
        await c.send_message(
            chat_id=cb.message.chat.id,
            text=f"GDV_{cb.message.message_id}\n"
                 "You have not given me a gdrive key as of yet. As a reply to this message, "
                 "send me the service account key.",
            reply_markup=ForceReply(True)
        )


@Client.on_message(filters.reply & filters.private & filters.document, group=3)
async def googleset_reply_msg_handler(c: Client, m: Message):
    func_message_obj = str(m.reply_to_message.text).splitlines()[0].split("_")
    key_file = f"working_dir/{secrets.token_hex(2)}.json"

    if len(func_message_obj) > 1:
        func = func_message_obj[0]

        if func == "GDV":
            await c.download_media(message=m.document, file_name=key_file)

            async with aiofiles.open(f"mega/{key_file}", mode='rb') as thumb:
                base64_key = base64.b64encode(await thumb.read())

            await MegaUsers().update_gdrive(m.from_user.id, base64_key, key_file)

            await m.reply_text(
                f"The key has been successfully attached. I will also provide you with a Gdrive link for the "
                f"files you upload here on {emoji.HANDSHAKE}"
            )
