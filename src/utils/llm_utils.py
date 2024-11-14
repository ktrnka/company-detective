import heapq
from typing import List


def heap_pair(doc: str) -> tuple:
    return (len(doc), doc)


def pack_documents(documents: List[str], max_chars: int, sep="\n\n") -> List[str]:
    """
    Pack documents into chunks of at most `max_chars` characters, unless there are some already over the limit

    This bin-packing algorithm will tend to make the bins all about the same size, but will tend to stop with many
    of the bins about max_chars/2 in size. It needs improvement
    """

    heap = [heap_pair(doc) for doc in documents]
    heapq.heapify(heap)

    while len(heap) >= 2:
        _, doc_a = heapq.heappop(heap)
        _, doc_b = heapq.heappop(heap)

        if len(doc_a) + len(doc_b) + len(sep) > max_chars:
            # put them back!
            heapq.heappush(heap, heap_pair(doc_a))
            heapq.heappush(heap, heap_pair(doc_b))
            break
        else:
            merged = f"{doc_a}{sep}{doc_b}"
            heapq.heappush(heap, heap_pair(merged))

    return [doc for _, doc in heap]


def test_pack_documents():
    documents = [
        "a",
        "b" * 2,
        "c" * 3,
        "d" * 4,
        "e" * 5,
    ]

    packed = pack_documents(documents, 6, sep="")

    assert len(packed) == 3
    assert all(len(doc) <= 6 for doc in packed)

    joined_packed = "\n\n".join(packed)
    assert all(doc in joined_packed for doc in documents)

    packed = pack_documents(documents, 10, sep="\n\n")
    assert len(packed) == 3
    assert all(len(doc) <= 10 for doc in packed)
    joined_packed = "\n\n".join(packed)
    assert all(doc in joined_packed for doc in documents)

    packed = pack_documents(documents, 10, sep="")
    assert len(packed) == 2
    assert all(len(doc) <= 10 for doc in packed)
    joined_packed = "\n\n".join(packed)
    assert all(doc in joined_packed for doc in documents)

    # check that it doesn't crash when there are not enough docs for packing
    pack_documents(documents[:2], 60, sep="")


def debug_around(substring: str, documents: List[str], context_chars=300):
    """Debug helper to find mangled URL sources in a list of documents"""
    for doc in documents:
        if substring in doc:
            i = doc.index(substring)
            start_index = max(0, i - context_chars // 2)
            end_index = min(len(doc), i + len(substring) + context_chars // 2)

            print("----")
            print(doc[start_index:end_index])
            print("----")


def cleanse_markdown(llm_markdown_output: str) -> str:
    """
    Sometimes LLM tools wrap markdown in a code block, which we need to remove in order to process it with markdown tools.
    """
    return llm_markdown_output.strip().strip("```markdown").strip("```").strip()
