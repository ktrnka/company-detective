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

    while True:
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