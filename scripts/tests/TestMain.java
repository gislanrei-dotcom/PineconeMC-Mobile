public final class TestMain {
    public static void main(String[] args) {
        System.out.println("PINECONE_RUNNER_OK:" + String.join("|", args));
        System.out.println("PINECONE_OPTION:" + System.getProperty("pinecone.test"));
    }
}
