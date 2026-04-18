# src/batch_processor.py

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable, Any
from tqdm.asyncio import tqdm_asyncio

class BatchProcessor:
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent

    async def process_files(self, filepaths: List[str], processor_function: Callable[[str], Any]) -> List[Any]:
        results = []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def worker(filepath: str) -> None:
            nonlocal results
            await semaphore.acquire()
            try:
                result = await asyncio.to_thread(processor_function, filepath)
                results.append(result)
            finally:
                semaphore.release()

        tasks = [worker(filepath) for filepath in filepaths]
        with tqdm_asyncio(total=len(tasks)) as pbar:
            async def update_pbar(future):
                await future
                pbar.update(1)

            await asyncio.gather(*(update_pbar(task) for task in tasks))
        return results

# Beispielverwendung:
if __name__ == "__main__":
    def process_file(filepath: str) -> str:
        # Hier den Code einfügen, um eine Datei zu verarbeiten
        with open(filepath, 'r') as file:
            content = file.read()
            print(f"Verarbeitet {filepath}")
        return f"Result for {filepath}"

    batch_processor = BatchProcessor(max_concurrent=4)
    filepaths = ["file1.txt", "file2.txt", "file3.txt", "file4.txt"]
    results = asyncio.run(batch_processor.process_files(filepaths, process_file))
    print(results)
