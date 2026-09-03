import com.sun.net.httpserver.HttpServer;
import java.io.OutputStream;
import java.net.InetSocketAddress;

public class Main {
    public static void main(String[] args) throws Exception {
        HttpServer httpNode = HttpServer.create(new InetSocketAddress(8080), 0);
        httpNode.createContext("/", txn -> {
            String payload = "<h1>Hello World from Vansh's Java app!</h1>";
            txn.sendResponseHeaders(200, payload.getBytes().length);
            OutputStream outStream = txn.getResponseBody();
            outStream.write(payload.getBytes());
            outStream.close();
        });
        httpNode.setExecutor(null);
        System.out.println("Java app listening on port 8080");
        httpNode.start();
    }
}
