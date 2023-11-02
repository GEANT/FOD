from django.core.mail.message import EmailMessage
from django.conf import settings
import os
import datetime

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "flowspec_accounts_view.log", False)

#

def send_new_mail(subject, message, from_email, recipient_list, bcc_list):
  try:
    logger.info("helpers::send_new_mail(): send mail: from_email="+str(from_email)+", recipient_list="+str(recipient_list)+", bcc_list="+str(bcc_list)) 
    return EmailMessage(subject, message, from_email, recipient_list, bcc_list).send()
  except Exception as e:
    #os.write(3, "send_new_mail() failed: exc="+str(e)+"\n") 
    logger.error("helpers::send_new_mail() failed: exc="+str(e)) 

def get_peer_techc_mails(user, peer):
    logger.info("helpers::get_peer_techc_mails(): user="+str(user)+", peer="+str(peer))
    mail = []
    additional_mail = []
    techmails_list = []
    user_mail = '%s' % user.email
    user_mail = user_mail.split(';')
    techmails = []
    if peer:
        techmails = peer.techc_emails.all()
    if techmails:
        for techmail in techmails:
            techmails_list.append(techmail.email)
    if settings.NOTIFY_ADMIN_MAILS:
        additional_mail = settings.NOTIFY_ADMIN_MAILS
    mail.extend(additional_mail)
    mail.extend(techmails_list)
    logger.info("helpers::get_peer_techc_mails(): additional_mail="+str(additional_mail))
    logger.info("helpers::get_peer_techc_mails(): techmails_list="+str(techmails_list))
    return mail

#

admin_error_mail_entry__cache_list = []
max_length_of_entry_message_text__in_digest_mail_text=1000

def handle_admin_error_mail(subject, message):
  try:

    global admin_error_mail_entry__cache_list

    logger.info("helpers::handle_admin_error_mail(): subject='"+str(subject)+"' message='"+str(message)+"'")

    admin_mail_addres_list = ""
    if settings.NOTIFY_ADMIN_MAILS:
      admin_mail_addres_list = settings.NOTIFY_ADMIN_MAILS        
   
    src_addr = settings.SERVER_EMAIL
    logger.info("helpers::handle_admin_error_mail(): src_addr="+str(src_addr))
    logger.info("helpers::handle_admin_error_mail(): admin_mail_addres_list="+str(admin_mail_addres_list))

    if admin_mail_addres_list:
      EmailMessage(subject, message, src_addr, admin_mail_addres_list, "").send()
    logger.info("helpers::handle_admin_error_mail(): after mail sending")

    nowtime = datetime.datetime.now()
    logger.info("helpers::handle_admin_error_mail(): nowtime="+str(nowtime))

    admin_error_mail_entry__cache_list.append({ 'time': nowtime, 'subject': subject, 'message': message })
    logger.info("helpers::handle_admin_error_mail(): after list append")

    return True

  except Exception as e:
    logger.error("helpers::handle_admin_error_mail() failed: exc="+str(e)) 
    return False

def send_cached_admin_error_entry_summary_ll():
  try:
    
    global admin_error_mail_entry__cache_list

    logger.info("helpers::send_cached_admin_error_entry_summary_ll(): called")

    admin_mail_addres_list = ""
    if settings.NOTIFY_ADMIN_MAILS:
      admin_mail_addres_list = settings.NOTIFY_ADMIN_MAILS        
    
    #

    if len(admin_mail_addres_list)>0:

      subject = 'FoD admin external error summary'
  
      mail_all_text = ''
  
      for entry in admin_error_mail_entry__cache_list:
        nowtime = entry['time']
        subject = entry['subject']
        message = entry['message']
      
        nowstr = nowtime.isoformat()
  
        message_part = str(message)
        if len(message)>max_length_of_entry_message_text__in_digest_mail_text:
            message_part = substr(message, 1, max_length_of_entry_message_text__in_digest_mail_text-4)+' ...' 
  
        mail_all_text = mail_all_text+'\n\n'+str(nowstr)+' '+str(subject)+':\n'+str(message_part)
  
      #
  
      logger.info("helpers::send_cached_admin_error_entry_summary_ll(): => mail_all_text='"+mail_all_text+"'")
  
      if admin_mail_addres_list:
        EmailMessage(subject, mail_all_text, settings.SERVER_EMAIL, admin_mail_addres_list, "").send()
  
      admin_mail_addres_list = [] 

    return True

  except Exception as e:
    logger.error("helpers::send_cached_admin_error_entry_summary_ll(): failed: exc="+str(e)) 
    return False


