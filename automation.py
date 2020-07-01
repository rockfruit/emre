#!/usr/bin/env python3
"""Intellect Macro Script

- Dependencies:

    Python
    Selenium
    Browsers
    Associated webdrivers

    (Tested with chrome and firefox)

- Requirements:

    $ pip install selenium

- Config:

    All the configuration is written at the top of this file

- Running:

    python automation.py

- Change the loglevel to WARNING after script is working

- If errors occur, screenshots are saved as *.png in the working directory

"""

import logging
import time
from typing import List
from typing import Optional
from typing import Union

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as CHOptions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FFOptions
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select

# loglevel = 'DEBUG'
loglevel = 'INFO'
# loglevel = 'WARNING'
# loglevel = 'ERROR'

browser = 'chrome'
headless = True

username = 'admin'
password = '1nt3ll3ct'

publish_timeout_minutes = 720
restore_timeout_minutes = 10
retries = 30
interval = 2
implicit_wait = 2
page_load_timeout = 120

logging.basicConfig(level=loglevel)
logger = logging.getLogger(__name__)
logger.setLevel(loglevel)


def main():
    design_index = -1
    while 1:
        design_index += 1
        site = Site(browser)
        try:
            # Restore publishdesign backup entry
            url = 'https://publishdesign.intellect.com/intellect/admin'
            try:
                restore_backup(site, url, design_index)
            except IndexError:
                msg = f'Design site backup index {design_index} not found! END.'
                logger.info(msg)
                raise IndexError(msg)
            # Restore publishlive backup entry
            url = 'https://publishlive.intellect.com/intellect/admin'
            index = 0
            restore_backup(site, url, index)
            # Publish
            publish(site)
        except IndexError:
            break
        except Exception as e:
            site.screenshot('uncaught-exception')
            logger.exception(f'Uncaught exception: {e}')
        logger.info('Webdriver QUIT')
        site.driver.quit()


def restore_backup(site, url, index):
    logger.info(f"----- RESTORE index={index} at {url} -----")
    site.activate_window('main')
    site.login(url)
    # Click Open Backup & Restore Window
    # (there will always be 1 backup however the name will change)
    site.click_backup_and_restore_a_btn()
    site.name_new_window('backup_and_restore', activate=True)
    # Click on Restore Tab and click Next
    site.select_restore_tab()
    # Select the first backup file to restore, and click Next,
    # click Restore (another pop up window will appear)
    site.restore_backup(index)
    # Type password and click OK
    site.name_new_window('password', activate=True)
    site.enter_popup_password()
    # wait five minutes for completion, and verify success
    site.activate_window('backup_and_restore')
    site.wait_for_restore_success(restore_timeout_minutes * 60)
    site.close_window('password')
    site.close_window('backup_and_restore')


def publish(site):
    logger.info("----- PUBLISH -----")
    site.activate_window('main')
    site.login('https://publishdesign.intellect.com/intellect/admin')

    # Go to publish Tab
    site.click('#SectionPublishButton')
    # Click on the publish button
    site.switch_to_frame('#PublishSites')
    site.click('#PublishButton_0')
    # Pop up screen will appear, click next
    site.name_new_window('publish', activate=True)
    site.click('#NextButton')
    # Uncheck backup publish site database (it will come as checked)
    site.click('#BackupPublishSite')
    # Click Publish
    site.click('#PublishButton')
    # a popup window will appear asking for password
    site.name_new_window('password', activate=True)
    # Type 1nt3ll3ct as password, then click OK
    # This will initiate the publish process, and system will 'do the rest'.
    site.enter_popup_password()
    time.sleep(0.5)
    site.close_window('password', then_focus='publish')

    # Once completed, pop up window will update with green success message.
    # If an error occurs, it will update the window with red error message.
    logger.info("Wait for 'Publish' action to complete")
    _status = ''
    for i in range(publish_timeout_minutes * 60):
        time.sleep(1)
        try:
            site.activate_window("publish", quiet=True)
            site.switch_to_default_content(quiet=True)
            try:
                el = site.find("span#lblPublishStatus")
            except Exception as e:
                site.screenshot('cant-find-lblPublishStatus')
                msg = f"Can't find span#lblPublishStatus: {e}: ABORT"
                logger.exception(msg)
                break
            status = el.text
            # Log status
            if status != _status:
                logger.info(status)
                _status = status
        except TimeoutException as e:
            logger.exception(e)
            site.screenshot('chrome-renderer-timeout-exception')
            _status = f"ignoring chrome renderer timeout"
            continue
        except Exception as e:
            logger.exception(e)
            continue
        # Error
        if 'Publish site database corrupted' in status:
            site.screenshot('publication-error')
            msg = f'Publication ERROR. ({status})'
            logger.error(msg)
            break
        # Warning
        elif 'Completed with Warnings' in status:
            site.screenshot('publication-warning')
            msg = f'Publication WARNING. ({status})'
            logger.warning(msg)
            break
        # SUCCESS
        elif 'Completed successfully' in status:
            msg = f'Publication Completed. ({status})'
            logger.warning(msg)
            break
        # OOPS
        if 'oops' in status.lower():
            site.screenshot('publication-exception')
            msg = f'Publication UNHANDLED ERROR. ({status})'
            logger.error(msg)
            break
        # "References Outside Designer Tab.
        elif len(site.driver.window_handles) > len(site.activated):
            site.name_new_window('expected_popup', activate=True)
            site.click('#OKButton')
            site.close_window('expected_popup', then_focus='publish')
            site.switch_to_default_content()
            continue
    else:
        msg = "Publication TIMEOUT ERROR."
        logger.warning(msg)


class Site:

    def __init__(self, driver_type: str):
        if driver_type == 'chrome':
            options = CHOptions()
            if headless:
                options.add_argument("--headless")
            options.add_argument("start-maximized")
            options.add_argument("enable-automation")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-browser-side-navigation")
            options.add_argument("--disable-gpu")
            self.driver = webdriver.Chrome(options=options)
        elif driver_type == 'firefox':
            options = FFOptions()
            options.headless = True
            self.driver = webdriver.Firefox(options=options)
        else:
            self.driver = getattr(webdriver, driver_type).webdriver.WebDriver()
        self.driver.implicitly_wait(implicit_wait)
        self.driver.set_page_load_timeout(page_load_timeout)
        self.activated = {}
        while not self.activated.get('main', None):
            self.activated['main'] = self.driver.current_window_handle
            self.active_window = 'main'
            time.sleep(0.2)

    def login(self, login_url):
        logger.info(f"Login at {login_url} as {username}:{password}")
        self.driver.get(login_url)
        self.send_keys('#Username', username, clear=True, tab=True)
        self.send_keys('#Password', password, clear=True, tab=True)
        self.click('#Button1')

    def screenshot(self, tag):
        n = str(time.time())
        fn = f'{tag}-{n}.png'
        self.driver.get_screenshot_as_file(fn)
        logger.warning(f'Screenshot saved as {fn}')
        return fn

    def click_backup_and_restore_a_btn(self):
        logger.info("Click Backup & Restore button (a.button)")
        self.click('a.button')

    def name_new_window(self, name, activate=None):
        activate = activate if activate else None
        if name in self.activated:
            msg = f'Window name used twice "{name}"'
            raise RuntimeError(msg)
        logger.info(f'Waiting for new window "{name}"')
        for i in range(5):
            handles = self.driver.window_handles
            new_wh = [h for h in handles if h not in self.activated.values()]
            if new_wh:
                self.activated[name] = new_wh[0]
                break
            time.sleep(1)
        else:
            msg = f'New window did not appear "{name}"'
            raise RuntimeError(msg)
        logger.info(f"{name}={self.activated[name]}")
        if activate:
            self.activate_window(name)
        time.sleep(1)

    def activate_window(self, name, quiet=False):
        self.switch_to_window(self.activated[name])
        self.active_window = name
        if not quiet:
            logger.info(f'Activated window "{name}"')

    def close_window(self, name, then_focus=None):
        then_focus = then_focus if then_focus else "main"
        try:
            wh = self.activated[name]
            self.switch_to_window(wh)
            self.driver.close()
        except Exception:  # noqa
            pass
        finally:
            del (self.activated[name])
            logger.info(f'Closed window {name}')
        self.activate_window(then_focus)

    def select_restore_tab(self):
        self.switch_to_frame('[name="Header"]')
        time.sleep(1)
        logger.info('Click link "RestoreDB"')
        self.click('a[href^="RestoreDB"]')

        time.sleep(1)
        self.switch_to_default_content()
        time.sleep(1)
        self.switch_to_frame('[name="Main"]')
        time.sleep(1)
        logger.info('Click #NextButton')
        self.click('#NextButton')
        self.page_contains_text('select the backup file that you want')

        self.switch_to_default_content()

    def restore_backup(self, index):
        self.switch_to_frame('[name="Main"]')
        options = self.list_options('select#lstDBBackupFiles')
        option = options[index]
        self.select_option('select#lstDBBackupFiles', option)
        time.sleep(1)
        self.click('#NextButton')
        self.click('#RestoreButton')

    def enter_popup_password(self):
        self.send_keys('#Password', password)
        self.click('#OK')

    def wait_for_restore_success(self, timeout):
        self.switch_to_frame('[name="Main"]')
        logger.info("Wait for restore to complete")
        try:
            self.switch_to_default_content(quiet=True)
            self.page_contains_text('Completed successfully', timeout, 1)
            logger.info('Restore Completed Successfully')
        except Exception as e:
            msg = f'Restore Failed ("Completed Successfully" not found) {e}'
            self.screenshot('restore-failed')
            raise RuntimeError(msg)

    def list_options(self, css):
        el = self.find(css)
        options = [o.text for o in el.options]
        optstr = '","'.join(options)
        logger.info(f'{css}: found {len(options)} options: "{optstr}"')
        return options

    def select_option(self, css, text):
        logger.info(f'selecting "{text}" from {css}')
        el = self.find(css)
        el.select_by_visible_text(text)

    def switch_to_window(self, window_handle):
        self.driver.switch_to.window(window_handle)

    def switch_to_frame(self, selector):
        time.sleep(1)
        self.driver.switch_to.default_content()
        time.sleep(1)
        logger.info(f'Switching to IFRAME with selector {selector}')
        frame = self.find(f'{selector}')
        self.driver.switch_to.frame(frame)
        time.sleep(1)

    def switch_to_default_content(self, quiet=False):
        if not quiet:
            logger.info("Switch focus to the default frame")
        self.driver.switch_to.default_content()

    def send_keys(self, el_or_css: Union[WebElement, str],
                  keys: Union[List, str], clear=True, tab=True,
                  expect: Optional[str] = None,
                  unexpect: Optional[Union[List[str], str]] = None):
        logger.info(f"Send keys {keys} to element {el_or_css}")
        el = self.find(el_or_css) if isinstance(el_or_css, str) else el_or_css
        if not el:
            msg = f"Can't find element specified by {el_or_css}"
            raise RuntimeError(msg)
        if isinstance(keys, list):
            for _keys in keys:
                self._send_keys(el, el_or_css, _keys, clear, tab, expect,
                                unexpect)
        else:
            self._send_keys(el, el_or_css, keys, clear, tab, expect, unexpect)

    def _send_keys(self, el, el_or_css, keys, clear, tab, expect, unexpect):
        if clear:
            el.clear()
        for key in keys:
            el.send_keys(key)
        if tab:
            el.send_keys(Keys.TAB)

        if expect and not self.page_contains_text(expect):
            logger.warning(f"Entered '{keys}' into '{el_or_css}': "
                           f"expected text not found: '{expect}'")

        if unexpect \
                and isinstance(unexpect, str) \
                and self.page_contains_text(unexpect):
            logger.warning(f"Entered '{keys}' into '{el_or_css}': "
                           f"unexpected text found: '{unexpect}'")

        if unexpect and isinstance(unexpect, list):
            for un in unexpect:
                if self.page_contains_text(un):
                    logger.warning(f"Entered '{keys}' into '{el_or_css}': "
                                   f"unexpected text found: '{un}'")

    def page_contains_text(self, text, retries=None, interval=None):
        interval = interval if interval else 1
        retries = retries if retries else 10
        for x in range(retries):
            try:
                if text in self.driver.page_source:
                    return True
            except WebDriverException:
                pass
            time.sleep(interval)

    def click(self, css, retries=None, interval=None):
        logger.info(f'Clicking {css}')
        self.find(css, retries, interval).click()

    def find(self, css, retries=None, interval=None):
        interval = interval if interval else 1
        retries = retries if retries else 10
        for x in range(1, retries):
            el = self.driver.find_element_by_css_selector(css)
            if el:
                if el.tag_name == 'select':
                    return Select(el)
                return el
            time.sleep(interval)
        return False

    def finds(self, css, retries=None, interval=None):
        interval = interval if interval else 1
        retries = retries if retries else 10
        for x in range(1, retries):
            els = self.driver.find_elements_by_css_selector(css)
            if els:
                return els
            time.sleep(interval)
        return []


if __name__ == '__main__':
    main()
