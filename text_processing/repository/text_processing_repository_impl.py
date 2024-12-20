import asyncio
import os
import re
from concurrent.futures.thread import ThreadPoolExecutor

import aiofiles

from template.utility.color_print import ColorPrinter
from text_processing.repository.text_processing_repository import TextProcessingRepository


class TextProcessingRepositoryImpl(TextProcessingRepository):
    __instance = None
    # executor = ThreadPoolExecutor(max_workers=2)

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)

        return cls.__instance

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()

        return cls.__instance

    async def postprocessingTextToBacklogs(self, generatedBacklogsText):
        pattern = r'\d+\. \*\*백로그 제목\*\*: (.*?)\n   - \*\*Success Criteria\*\*: (.*?)\n   - \*\*도메인 이름\*\*: (.*?)\n   - \*\*To-do 목록\*\*:(.*?)(?=\n\n|$)'
        backlogItems = re.findall(pattern, generatedBacklogsText, re.DOTALL)
        backlogList = []
        for item in backlogItems:
            backlog = {
                'title': item[0].strip(),
                'success_criteria': item[1].strip(),
                'domain': item[2].strip(),
                'task_list': [f"{task.strip()}" for task in item[3].split("\n") if task.strip()]
            }
            backlogList.append(backlog)

        return backlogList

    async def process_file(self, filePath):
        async with aiofiles.open(filePath, mode='r', encoding='utf-8') as f:
            content = await f.read()
            if len(content) < 512:
                return ""
        return f"File: {filePath}\n{content}\n"

    async def async_os_walk(self, path):
        ColorPrinter.print_important_message("async_os_walk()")
        try:
            # Run the os.walk in a thread to avoid blocking the event loop
            files = await asyncio.to_thread(lambda: list(os.walk(path)))
            return files
        except Exception as e:
            ColorPrinter.print_important_message(f"Error during os.walk: {e}")
            return []

    async def getTextFromSourceCode(self, githubRepositoryPath):
        ColorPrinter.print_important_data("getTextFromSourceCode()", githubRepositoryPath)
        text = ""

        tasks = []
        osPath = await self.async_os_walk(githubRepositoryPath)
        ColorPrinter.print_important_data("getTextFromSourceCode() osPath", osPath)
        for root, dirs, files in osPath:
            for file in files:
                name, ext = os.path.splitext(file)
                if ext == ".py":
                    filePath = os.path.join(root, file)
                    tasks.append(self.process_file(filePath))

        results = await asyncio.gather(*tasks)

        for result in results:
            text += result

        return text

    async def extractSections(self, text: str):
        pattern_map = {
            "title": r"### 프로젝트 제목\s*-\s*(.*)### 프로젝트 개요",
            "overview": r"### 프로젝트 개요\s*-*\s*(.*)### 기술 스택",
            "tech_stack": r"### 기술 스택(.*?)### 주요 기능",
            "features": r"### 주요 기능(.*?)### 활용 방안",
            "usage": r"### 활용 방안\s*-*\s*(.*)### 보완할 점",
            "improvement": r"### 보완할 점(.*?)### 완성도",
            "completion": r"### 완성도(.*)"
        }

        # 추출 결과를 저장할 딕셔너리 생성
        sections = {}

        for key, pattern in pattern_map.items():
            result = re.search(pattern, text, re.DOTALL)
            if result:
                sections[key] = result.group(1).strip()
            else:
                sections[key] = ""

        return sections

    async def extractTechStack(self, text):
        languagePattern = r"-\s*\*\*언어\*\*:\s*(.*)"
        frameworkPattern = r"-\s*\*\*프레임워크\*\*:\s*(.*)"

        languageMatch = re.search(languagePattern, text)
        language = languageMatch.group(1).strip() if languageMatch else ""

        if language:
            language = language.split(", ")

        frameworkMatch = re.search(frameworkPattern, text)
        framework = frameworkMatch.group(1).strip() if frameworkMatch else ""

        if framework:
            framework = framework.split(", ")

        result = []
        for lang in language:
            result.append(lang)
        for frame in framework:
            result.append(frame)

        return result

    async def extractFeatures(self, text):
        # pattern = r'### (.*?)\n(.*?)(?=\n\n|\Z)'

        #
        # matches = re.findall(pattern, text, re.DOTALL)
        #
        # extractedFeatures = []
        #
        # for match in matches:
        #     title, content = match
        #     combinedFeatures = f"{title.strip()}: \n{content.strip()}"
        #     extractedFeatures.append(combinedFeatures)
        pattern = r"(####\s*.+?)(?=(####|$))"

        matches = re.findall(pattern, text, re.DOTALL)

        extractedFeatures = []

        for match in matches:
            section_text = match[0].strip()
            lines = section_text.split('\n', 1)
            title = lines[0].strip()
            content = lines[1].strip() if len(lines) > 1 else ""
            extractedFeatures.append(f"{title}\n{content}")

        return extractedFeatures

    async def extractScore(self, score):
        extractedScores = []  # 점수와 상세 정보를 담을 리스트

        # 모든 섹션을 한 번에 추출
        # pattern = r'### (?:보안|유지보수|전체):\n- \*\*점수\*\*: (\d+)점\n- \*\*상세 정보\*\*: (.*?)\n\n'
        pattern = r'### (?:보안|유지보수|전체): (\d+)\n- (.*?)\n'
        matches = re.findall(pattern, score + '\n\n', re.DOTALL)

        for match in matches:
            extractedScores.append([match[0], match[1].strip()])

        return extractedScores
