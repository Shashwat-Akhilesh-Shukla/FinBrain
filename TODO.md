# Migration from Qdrant to Pinecone - TODO List

- [x] Update `vectordb_storage.py` to use Pinecone client instead of Qdrant
- [x] Rename function `store_pdfs_in_qdrant` to `store_pdfs_in_pinecone` in `vectordb_storage.py`
- [x] Update `requirements.txt` to replace `qdrant_client` with `pinecone-client`
- [x] Remove Qdrant service from `docker-compose.yml`
- [x] Update imports in `app.py` to use the new function name
- [x] Update imports in `llmintegration.py` to use the new function name
- [ ] Test the app locally after changes
- [ ] Verify Pinecone index creation and data upsert/query
- [ ] Ensure Docker build and run work without Qdrant
