def chunk_text(text, max_chunk=512):
    return [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]

def summarize_chunks(summarizer, text, max_length=200, min_length=50):
    chunks = chunk_text(text)
    summarized_chunks = []
    for chunk in chunks:
        summary = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
        summarized_chunks.append(summary[0]['summary_text'])
    return "\n".join(summarized_chunks)